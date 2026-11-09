"""Historical cash intake defined by design/02 §3.9; uses the single SQLite World."""

from __future__ import annotations

from urllib.parse import quote

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import GateIssue, QuarantineRecord
from recoup.contracts.money import Money
from recoup.contracts.remittance import (
    CasePaymentAllocation,
    RemittanceBundle,
    RemittanceLoadResult,
)

from .hashing import canonical, digest


def initialize(world) -> None:
    world.db.executescript("""
        CREATE TABLE IF NOT EXISTS remittances (
            id TEXT NOT NULL, version INTEGER NOT NULL, buyer_id TEXT NOT NULL,
            payment_ref TEXT NOT NULL, payload_hash TEXT NOT NULL,
            payload TEXT NOT NULL, data TEXT NOT NULL,
            PRIMARY KEY(id,version));
        CREATE TABLE IF NOT EXISTS remittance_outcomes (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL,
            payload_hash TEXT NOT NULL, data TEXT NOT NULL,
            UNIQUE(id,payload_hash,data));
        CREATE TABLE IF NOT EXISTS remittance_sources (
            buyer_id TEXT NOT NULL, payment_ref TEXT NOT NULL, remittance_id TEXT NOT NULL,
            PRIMARY KEY(buyer_id,payment_ref));
    """)


def history(world, remittance_id: str | None = None) -> list[RemittanceLoadResult]:
    query = "SELECT data FROM remittance_outcomes"
    params = ()
    if remittance_id is not None:
        query += " WHERE id=?"
        params = (remittance_id,)
    return [
        RemittanceLoadResult.model_validate_json(row[0])
        for row in world.db.execute(query + " ORDER BY seq", params)
    ]


def _audit(world, bundle, result, payload_hash):
    world.db.execute(
        "INSERT OR IGNORE INTO remittance_outcomes(id,payload_hash,data) VALUES(?,?,?)",
        (bundle.remittance_id, payload_hash, result.model_dump_json()),
    )


def _result(bundle, status, code, message):
    return RemittanceLoadResult(
        remittance_id=bundle.remittance_id,
        version=bundle.version,
        status=status,
        issues=[GateIssue(code=code, message=message)],
    )


def _save(world, bundle, result, payload_hash):
    _audit(world, bundle, result, payload_hash)
    world.db.execute(
        "INSERT INTO remittances VALUES(?,?,?,?,?,?,?)",
        (
            bundle.remittance_id,
            bundle.version,
            bundle.buyer_id,
            bundle.payment_ref,
            payload_hash,
            bundle.model_dump_json(),
            result.model_dump_json(),
        ),
    )


def load(world, bundle: RemittanceBundle, bundle_dir: str | None = None) -> RemittanceLoadResult:
    payload_hash = digest(canonical(bundle.model_dump(mode="json")))
    with world.transaction():
        previous = world.db.execute(
            "SELECT * FROM remittances WHERE id=? ORDER BY version DESC", (bundle.remittance_id,)
        ).fetchall()
        same = next((row for row in previous if row["version"] == bundle.version), None)
        if same:
            if same["payload_hash"] == payload_hash:
                return RemittanceLoadResult.model_validate_json(same["data"]).model_copy(
                    update={"replay": True}
                )
        if bundle.currency != "USD" or any(case.currency != "USD" for case in bundle.cases):
            q = QuarantineRecord(
                case_id=f"remittance:{bundle.remittance_id}",
                reason="Unsupported remittance currency",
                raw_bundle_json=bundle.model_dump_json(),
                at=world.clock.now(),
            )
            world._save("quarantine", q, q.case_id, q.case_id, replace=True)
            result = _result(bundle, "quarantined", "unsupported_currency", q.reason)
            if same:
                _audit(world, bundle, result, payload_hash)
            else:
                _save(world, bundle, result, payload_hash)
            return result
        if same:
            result = _result(
                bundle, "needs_human", "remittance_conflict", "Same revision has different content"
            )
            _audit(world, bundle, result, payload_hash)
            return result
        if previous:
            first = world.db.execute(
                "SELECT payload FROM remittances WHERE id=? ORDER BY rowid LIMIT 1",
                (bundle.remittance_id,),
            ).fetchone()
            original = RemittanceBundle.model_validate_json(first[0])
            if (bundle.buyer_id, bundle.payment_ref) != (original.buyer_id, original.payment_ref):
                result = _result(
                    bundle,
                    "needs_human",
                    "remittance_bank_identity",
                    "Bank source identity is immutable",
                )
                _save(world, bundle, result, payload_hash)
                return result
        if previous and (
            bundle.version <= previous[0]["version"]
            or any(
                RemittanceLoadResult.model_validate_json(row["data"]).allocations
                for row in previous
            )
        ):
            result = _result(
                bundle, "needs_human", "remittance_immutable", "Posted cash cannot be reallocated"
            )
            _save(world, bundle, result, payload_hash)
            return result
        source = world.db.execute(
            "SELECT remittance_id FROM remittance_sources WHERE buyer_id=? AND payment_ref=?",
            (bundle.buyer_id, bundle.payment_ref),
        ).fetchone()
        if source and source[0] != bundle.remittance_id:
            result = _result(
                bundle, "needs_human", "duplicate_payment", "Bank payment already has an intake"
            )
            _save(world, bundle, result, payload_hash)
            return result
        try:
            with world.transaction():
                result = _apply(world, bundle, bundle_dir)
        except (GateError, ValueError) as exc:
            issues = (
                exc.issues
                if isinstance(exc, GateError)
                else [GateIssue(code="invalid_remittance", message=str(exc))]
            )
            result = RemittanceLoadResult(
                remittance_id=bundle.remittance_id,
                version=bundle.version,
                status="needs_info",
                unapplied=Money(cents=bundle.paid_cents),
                issues=issues,
            )
        world.db.execute(
            "INSERT OR IGNORE INTO remittance_sources VALUES(?,?,?)",
            (bundle.buyer_id, bundle.payment_ref, bundle.remittance_id),
        )
        _save(world, bundle, result, payload_hash)
        return result


def _apply(world, bundle, bundle_dir):
    if len({case.case_id for case in bundle.cases}) != len(bundle.cases):
        world._error("duplicate_case", "Duplicate child case identity")
    initialized = world.db.execute("SELECT 1 FROM meta WHERE key='start_date'").fetchone()
    effective_date = (
        world.clock.now().date() if initialized or not bundle.cases else bundle.cases[0].start_date
    )
    if bundle.paid_date > effective_date:
        world._error("future_payment", "Historical cash cannot have a future paid date")
    supplied = {case.case_id: case for case in bundle.cases}
    all_cases = {
        row["id"]: CaseBundle.model_validate_json(row["data"])
        for row in world.db.execute("SELECT id,data FROM cases")
    }
    for case_id, case in supplied.items():
        if case_id in all_cases and all_cases[case_id] != case:
            world._error("case_exists", case_id)
        all_cases[case_id] = case
    if not all((bundle.remittance_id.strip(), bundle.payment_ref.strip(), bundle.buyer_id.strip())):
        world._error("missing_identity", "Remittance identities must be nonempty")
    invoices = {}
    case_buyers = {}
    case_docs = {}
    for case_id, case in all_cases.items():
        exists = world.db.execute("SELECT 1 FROM cases WHERE id=?", (case_id,)).fetchone()
        if exists:
            docs = world.active_evidence(case_id)
        else:
            newest = {}
            for doc in case.docs:
                if doc.available_at_day <= world.clock.day() and doc.held_by is None:
                    if doc.doc_ref not in newest or doc.version > newest[doc.doc_ref].version:
                        newest[doc.doc_ref] = doc
            docs = list(newest.values())
        case_docs[case_id] = docs
        for doc in docs:
            if doc.kind != "invoice" or doc.doc_ref != case.invoice_ref:
                continue
            fields = doc.fields.copy()
            if exists:
                fields.update(
                    {
                        key: fact.value
                        for (eid, key), fact in world._latest_facts(case_id).items()
                        if eid == doc.evidence_id
                    }
                )
            invoice_no = fields.get("invoice_no")
            buyer_id = fields.get("buyer_id")
            case_buyers[case_id] = buyer_id
            if isinstance(invoice_no, str) and invoice_no:
                invoices.setdefault(invoice_no, []).append((case_id, buyer_id))
    for case_id, docs in case_docs.items():
        if case_buyers.get(case_id) != bundle.buyer_id:
            continue
        for doc in docs:
            if (
                doc.kind == "payment"
                and doc.fields.get("payment_ref", doc.doc_ref) == bundle.payment_ref
            ):
                world._error("payment_already_intaken", "Matching bank cash was already intaken")
    # Historical superseded payment evidence still owns the immutable ledger posting.
    for evidence in world._rows("evidence"):
        if (
            case_buyers.get(evidence.case_id) == bundle.buyer_id
            and evidence.kind == "payment"
            and evidence.fields.get("payment_ref", evidence.doc_ref) == bundle.payment_ref
            and any(entry.source == evidence.doc_ref for entry in world.ledger(evidence.case_id))
        ):
            world._error("payment_already_intaken", "Matching bank cash was already intaken")
    refs = [allocation.invoice_no for allocation in bundle.allocations]
    if len(set(refs)) != len(refs):
        world._error("duplicate_invoice_ref", "Invoice references must be unique")
    if sum(allocation.paid_cents for allocation in bundle.allocations) > bundle.paid_cents:
        world._error("allocation_exceeds_cash", "Requested allocations exceed bank cash")
    matched = []
    for allocation in bundle.allocations:
        candidates = invoices.get(allocation.invoice_no, [])
        if len(candidates) != 1:
            world._error("invoice_reference", "Unmatched or ambiguous exact invoice reference")
        case_id, buyer_id = candidates[0]
        if buyer_id != bundle.buyer_id:
            world._error("buyer_mismatch", "Invoice buyer does not match bank cash buyer")
        matched.append((allocation, case_id))
    results = [world.load_bundle(case, bundle_dir) for case in bundle.cases]
    allocations = []
    for allocation, case_id in matched:
        amount = min(allocation.paid_cents, max(0, world.ledger_balance(case_id).cents))
        ref = f"remittance:{quote(bundle.remittance_id, safe='')}"
        payment_ref = f"{ref}:allocation:{quote(allocation.invoice_no, safe='')}"
        for evidence in world._evidence_rows(case_id):
            if evidence.doc_ref not in {ref, payment_ref}:
                continue
            own_previous_audit = (
                evidence.doc_ref == ref
                and evidence.kind == "remittance"
                and evidence.version < bundle.version
                and evidence.fields.get("remittance_id") == bundle.remittance_id
                and evidence.fields.get("payment_ref") == bundle.payment_ref
                and evidence.fields.get("buyer_id") == bundle.buyer_id
            )
            if not own_previous_audit:
                world._error(
                    "remittance_evidence_conflict", "Remittance source evidence already exists"
                )
        if any(entry.source == payment_ref for entry in world.ledger(case_id)):
            world._error("remittance_evidence_conflict", "Allocated cash already exists")
        audit = world.add_evidence(
            case_id,
            BundleDoc(
                doc_ref=ref,
                version=bundle.version,
                kind="remittance",
                title="SYNTHETIC remittance source audit",
                text=bundle.model_dump_json(),
                fields={
                    "remittance_id": bundle.remittance_id,
                    "payment_ref": bundle.payment_ref,
                    "buyer_id": bundle.buyer_id,
                    "paid_cents": bundle.paid_cents,
                    "paid_date": bundle.paid_date.isoformat(),
                    "provenance": "synthetic",
                },
            ),
        )
        if audit is None:
            world._error("remittance_evidence_conflict", "Remittance audit was not added")
        if amount == 0:
            continue
        payment = world.add_evidence(
            case_id,
            BundleDoc(
                doc_ref=payment_ref,
                version=bundle.version,
                kind="payment",
                title="SYNTHETIC allocated historical cash",
                fields={
                    "paid_cents": amount,
                    "paid_date": bundle.paid_date.isoformat(),
                    "invoice_no": allocation.invoice_no,
                    "payment_ref": bundle.payment_ref,
                    "remittance_ref": ref,
                    "provenance": "synthetic",
                },
            ),
        )
        if payment is None or not any(
            entry.source == payment_ref and entry.kind == "payment" and entry.amount.cents == amount
            for entry in world.ledger(case_id)
        ):
            world._error("remittance_payment_missing", "Allocated payment did not post")
        allocations.append(
            CasePaymentAllocation(
                case_id=case_id, invoice_no=allocation.invoice_no, amount=Money(cents=amount)
            )
        )
    return RemittanceLoadResult(
        remittance_id=bundle.remittance_id,
        version=bundle.version,
        status="loaded",
        results=results,
        allocations=allocations,
        unapplied=Money(cents=bundle.paid_cents - sum(a.amount.cents for a in allocations)),
    )
