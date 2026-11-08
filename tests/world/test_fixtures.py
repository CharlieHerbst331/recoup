"""Validate synthetic fixture inputs independently; refs: design/02 §3.7, §8.1."""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.models import DeductionReason, DocKind, ProposalKind
from recoup.contracts.oracle import CaseOracle

CASES = Path(__file__).resolve().parents[2] / "cases"
BUNDLES = sorted(CASES.glob("demo/*/bundle.json")) + sorted(CASES.glob("regression/*/bundle.json"))
REGRESSIONS = sorted(CASES.glob("regression/*/bundle.json"))


def read_bundle(path: Path) -> CaseBundle:
    return CaseBundle.model_validate_json(path.read_text())


def read_oracle(path: Path) -> CaseOracle:
    return CaseOracle.model_validate_json(path.with_name("oracle.json").read_text())


def all_docs(bundle: CaseBundle) -> list[BundleDoc]:
    return [*bundle.docs, *(event.doc for event in bundle.events)]


def by_ref(bundle: CaseBundle, ref: str) -> BundleDoc:
    return next(doc for doc in bundle.docs if doc.doc_ref == ref)


# Validation vectors for the published vocabulary; see design/02 §3.7.
CONTRACT_KEYS = {
    "contract_id",
    "effective_date",
    "early_pay_bp",
    "early_pay_days",
    "late_penalty_bp",
    "late_grace_days",
    "damage_window_days",
    "damage_late_waived",
    "returns_require_rma",
    "required_delivery_date",
}
AMENDMENT_KEYS = {"amends", "effective_date", "authorized_by", "authority_role"}
EXACT_KEYS = {
    DocKind.invoice: {"invoice_no", "invoice_date", "due_date", "buyer_id", "total_cents"},
    DocKind.payment: {"invoice_no", "paid_cents", "paid_date", "payment_ref"},
    DocKind.remittance: {"invoice_no", "paid_cents"},
    DocKind.debit_memo: {"invoice_no"},
    DocKind.po: {"po_no", "required_delivery_date"},
    DocKind.contract: CONTRACT_KEYS,
    DocKind.amendment: CONTRACT_KEYS | AMENDMENT_KEYS,
    DocKind.bol: {"bol_no", "ship_date"},
    DocKind.pod: {"pod_no", "delivered_date", "signed", "exception_note"},
    DocKind.inspection: {"report_date", "sku", "damaged_qty", "cause"},
    DocKind.return_auth: {"rma_no", "sku", "authorized_qty", "received_qty", "received_date"},
    DocKind.credit_memo: {"credit_no", "invoice_no", "amount_cents", "line_id"},
    DocKind.statement: {"as_of", "balance_cents"},
    DocKind.collection_note: {"date", "channel"},
    DocKind.company_policy: {
        "tolerance_cents",
        "follow_up_days",
        "authority_cents",
        "allowed_authority_roles",
        "amendment_precedence",
    },
    DocKind.insurance_policy: {
        "policy_id",
        "credit_limit_cents",
        "period_start",
        "period_end",
        "mep_days_after_due",
        "notice_days_after_mep",
        "waiting_days_after_notice",
        "disputed_debt_clause",
        "stop_shipment_after_mep",
    },
    DocKind.email: {"from", "to", "sent_date"} | CONTRACT_KEYS | AMENDMENT_KEYS,
}
LINE_KEY = r"line\.[1-9][0-9]*\.(sku|qty|unit_price_cents)"
DEDUCTION_KEY = (
    r"ded\.[1-9][0-9]*\."
    r"(line_id|reason|claimed_cents|sku|qty|ref|reported_date)"
)
CONTRACT_PATTERNS = [r"price\.[A-Z0-9_-]+_cents", r"promo\.[A-Z0-9_-]+\.(cap_cents|earned)"]
PATTERNS = {
    DocKind.invoice: [LINE_KEY],
    DocKind.po: [LINE_KEY],
    DocKind.remittance: [DEDUCTION_KEY],
    DocKind.debit_memo: [DEDUCTION_KEY],
    DocKind.contract: CONTRACT_PATTERNS,
    DocKind.amendment: CONTRACT_PATTERNS,
    DocKind.email: CONTRACT_PATTERNS,
    DocKind.pod: [r"(received|refused)\.[A-Z0-9_-]+"],
    DocKind.bol: [r"shipped\.[A-Z0-9_-]+"],
    DocKind.insurance_policy: [
        r"covered_buyer\.[1-9][0-9]*",
        r"claim_doc\.[1-9][0-9]*",
        r"clause\.[a-z_]+",
        r"exclusion\.[1-9][0-9]*",
    ],
}


@pytest.mark.parametrize("path", BUNDLES, ids=lambda p: str(p.relative_to(CASES)))
def test_bundle_schema_vocabulary_and_raw_scalar_types(path):
    bundle = read_bundle(path)
    assert bundle.provenance == "synthetic"
    assert bundle.title.startswith("SYNTHETIC")
    assert bundle.static_day >= 0
    raw = json.loads(path.read_text())
    raw_docs = [*raw["docs"], *(event["doc"] for event in raw["events"])]
    for source, doc in zip(raw_docs, all_docs(bundle), strict=True):
        assert doc.title.startswith("SYNTHETIC")
        assert "SYNTHETIC" in doc.text
        assert doc.version > 0
        assert doc.available_at_day >= 0
        for key, value in source["fields"].items():
            assert key in EXACT_KEYS.get(doc.kind, set()) or any(
                re.fullmatch(pattern, key) for pattern in PATTERNS.get(doc.kind, [])
            ), (doc.kind, key)
            assert value is None or type(value) in {str, int, bool}, key
            if key.endswith(("_cents", "_bp")):
                assert type(value) is int, key
            if key.endswith(".reason"):
                assert value in {reason.value for reason in DeductionReason}
            if key.startswith("claim_doc."):
                assert value in {kind.value for kind in DocKind}
            if key in {
                "signed",
                "damage_late_waived",
                "returns_require_rma",
                "stop_shipment_after_mep",
            } or key.endswith(".earned"):
                assert type(value) is bool, key
            if key.endswith("_date") or key in {"as_of", "period_start", "period_end", "date"}:
                date.fromisoformat(value)
        if doc.kind == DocKind.insurance_policy:
            for key, value in doc.fields.items():
                if key.startswith("exclusion."):
                    assert f"clause.{value}" in doc.fields
    assert len({(doc.doc_ref, doc.version) for doc in all_docs(bundle)}) == len(all_docs(bundle))
    if bundle.policy_ref:
        assert by_ref(bundle, bundle.policy_ref).kind == DocKind.insurance_policy
    for recipients in bundle.allowed_recipients.values():
        assert recipients
        assert all(recipient.endswith(".invalid") for recipient in recipients)


@pytest.mark.parametrize("path", BUNDLES, ids=lambda p: str(p.relative_to(CASES)))
def test_invoice_payment_and_deduction_cents_reconcile(path):
    bundle = read_bundle(path)
    invoice = next(doc for doc in bundle.docs if doc.kind == DocKind.invoice)
    assert invoice.fields["invoice_no"] == bundle.invoice_ref
    fields = invoice.fields
    indexes = [
        key.removeprefix("line.").removesuffix(".qty")
        for key in fields
        if re.fullmatch(r"line\.[1-9][0-9]*\.qty", key)
    ]
    assert (
        sum(fields[f"line.{i}.qty"] * fields[f"line.{i}.unit_price_cents"] for i in indexes)
        == fields["total_cents"]
    )
    paid = sum(doc.fields["paid_cents"] for doc in bundle.docs if doc.kind == DocKind.payment)
    credited = sum(
        doc.fields["amount_cents"] for doc in bundle.docs if doc.kind == DocKind.credit_memo
    )
    gap = fields["total_cents"] - paid - credited
    assert gap >= 0
    deductions = [
        value
        for doc in bundle.docs
        if doc.kind in {DocKind.remittance, DocKind.debit_memo}
        for key, value in doc.fields.items()
        if key.endswith(".claimed_cents")
    ]
    if deductions:
        assert sum(deductions) == gap
    for doc in bundle.docs:
        if doc.kind == DocKind.remittance:
            assert doc.fields["paid_cents"] == paid
        if "invoice_no" in doc.fields:
            assert doc.fields["invoice_no"] == bundle.invoice_ref
    if path.parent.name == "H":
        assert gap == 624000
        assert gap - 180000 == 444000
        assert gap - 180000 - 312000 == 132000


@pytest.mark.parametrize("path", REGRESSIONS, ids=lambda p: p.parent.name)
def test_regression_oracle_schema_refs_and_money(path):
    bundle, oracle = read_bundle(path), read_oracle(path)
    assert oracle.case_id == bundle.case_id
    assert oracle.expected_status == ("loaded" if bundle.currency == "USD" else "quarantined")
    raw = json.loads(path.with_name("oracle.json").read_text())
    assert oracle.oracle_sentinel not in path.read_text()
    assert oracle.oracle_sentinel.startswith("ORACLE-ONLY-SYNTHETIC-")
    assert len({line.line_id for line in oracle.lines}) == len(oracle.lines)
    declared = {
        doc.fields[key.removesuffix("claimed_cents") + "line_id"]: value
        for doc in bundle.docs
        for key, value in doc.fields.items()
        if key.endswith(".claimed_cents")
    }
    gap = by_ref(bundle, "INV").fields["total_cents"] - sum(
        doc.fields["paid_cents"] for doc in bundle.docs if doc.kind == DocKind.payment
    )
    for source, line in zip(raw["lines"], oracle.lines, strict=True):
        assert set(line.required_refs) <= set(line.acceptable_refs)
        for ref in line.acceptable_refs:
            doc_ref, marker, locator = ref.partition("#")
            evidence = by_ref(bundle, doc_ref)
            if marker:
                assert locator.startswith("fields.")
                assert locator.removeprefix("fields.") in evidence.fields
        if line.verdict == "needs_info":
            assert line.valid_cents is None and line.disputed_cents is None
            assert line.missing
        else:
            assert type(source["valid_cents"]) is int
            assert type(source["disputed_cents"]) is int
            assert line.valid_cents >= 0 and line.disputed_cents >= 0
            assert line.valid_cents + line.disputed_cents == declared.get(line.line_id, gap)
            if line.verdict == "valid":
                assert line.disputed_cents == 0
            elif line.verdict == "invalid":
                assert line.valid_cents == 0 and line.disputed_cents > 0
            else:
                assert line.valid_cents > 0 and line.disputed_cents > 0
    for source, proposal in zip(raw["proposals"], oracle.proposals, strict=True):
        assert proposal.kind not in oracle.forbidden_kinds
        assert set(proposal.line_ids) <= {line.line_id for line in oracle.lines}
        assert source["amount_cents"] is None or type(source["amount_cents"]) is int
        if proposal.kind in {ProposalKind.credit_memo, ProposalKind.dispute}:
            amount_key = (
                "valid_cents" if proposal.kind == ProposalKind.credit_memo else "disputed_cents"
            )
            assert proposal.amount_cents == sum(
                getattr(line, amount_key)
                for line in oracle.lines
                if line.line_id in proposal.line_ids
            )
    if oracle.expected_status == "quarantined":
        assert oracle.lines == oracle.proposals == []
        assert oracle.notice_deadline is None and oracle.claim_items == {}


def test_fixture_inventory_and_all_nine_reason_coverage():
    assert {path.parent.name for path in REGRESSIONS} == {f"r{i:02}" for i in range(1, 9)}
    assert {path.parent.name for path in BUNDLES if "demo" in path.parts} == {"H", "C", "N"}
    reasons = {
        value
        for path in REGRESSIONS
        for doc in read_bundle(path).docs
        for key, value in doc.fields.items()
        if key.endswith(".reason")
    }
    for path in REGRESSIONS:
        for line in read_oracle(path).lines:
            if line.line_id == "U1":
                reasons.add("unexplained_short_pay")
            if line.line_id == "NP":
                reasons.add("nonpayment")
    assert reasons == {reason.value for reason in DeductionReason}


def test_policy_documents_are_reused_without_drift_and_have_contrasting_terms():
    policies = {
        ref: BundleDoc.model_validate_json((CASES / "policies" / f"{ref}.json").read_text())
        for ref in ("P-A", "P-B")
    }
    for path in BUNDLES:
        bundle = read_bundle(path)
        if bundle.policy_ref:
            assert by_ref(bundle, bundle.policy_ref) == policies[bundle.policy_ref]
    a, b = policies["P-A"].fields, policies["P-B"].fields
    assert (
        a["mep_days_after_due"],
        a["notice_days_after_mep"],
        a["waiting_days_after_notice"],
    ) == (60, 30, 60)
    assert (b["mep_days_after_due"], b["notice_days_after_mep"]) == (90, 15)
    assert a["disputed_debt_clause"] == "excluded_until_resolved"
    assert b["disputed_debt_clause"] == "notice_still_required"


def test_hero_day_three_and_policy_calendar_match_demo():
    bundle = read_bundle(CASES / "demo/H/bundle.json")
    assert bundle.start_date == date(2026, 10, 20)
    assert all(doc.kind != DocKind.statement for doc in all_docs(bundle))
    v1 = by_ref(bundle, "POD")
    assert v1.version == 1 and v1.fields["signed"] is True
    assert v1.fields["received.SKU-1"] == 400
    assert len(bundle.events) == 2 and {event.at_day for event in bundle.events} == {3}
    v2 = next(event.doc for event in bundle.events if event.doc.kind == DocKind.pod)
    inspection = next(event.doc for event in bundle.events if event.doc.kind == DocKind.inspection)
    assert v2.doc_ref == v1.doc_ref and v2.version == 2
    assert v2.fields["signed"] is True
    assert v2.fields["received.SKU-1"] == 360 and v2.fields["refused.SKU-1"] == 40
    assert v2.fields["exception_note"] == "40 cs crushed, refused at dock"
    assert inspection.fields["damaged_qty"] == 40
    delivered = date.fromisoformat(v2.fields["delivered_date"])
    reported = date.fromisoformat(inspection.fields["report_date"])
    assert (reported - delivered).days <= by_ref(bundle, "TERMS").fields["damage_window_days"]
    terms = by_ref(bundle, "P-A").fields
    due = date.fromisoformat(by_ref(bundle, "INV").fields["due_date"])
    mep_end = due + timedelta(days=terms["mep_days_after_due"])
    deadline = mep_end + timedelta(days=terms["notice_days_after_mep"])
    assert mep_end == date(2026, 11, 1)
    assert deadline == date(2026, 12, 1) == bundle.start_date + timedelta(days=42)
    assert deadline - timedelta(days=7) == bundle.start_date + timedelta(days=35)
    assert 35 + terms["waiting_days_after_notice"] == 95


def test_authorized_demo_and_unauthorized_regression_amendments():
    demo = read_bundle(CASES / "demo/C/bundle.json")
    amendment = by_ref(demo, "PRICE-AMENDMENT")
    allowed = by_ref(demo, "COMPANY").fields["allowed_authority_roles"].split(",")
    assert amendment.kind == DocKind.email
    assert amendment.fields["authority_role"] in allowed
    assert amendment.fields["authorized_by"]
    assert amendment.fields["effective_date"] <= by_ref(demo, "INV").fields["invoice_date"]
    assert (1050 - amendment.fields["price.SKU-7_cents"]) * 1000 == 50000
    unauthorized = read_bundle(CASES / "regression/r01/bundle.json")
    assert by_ref(unauthorized, "UNAUTHORIZED").fields["authority_role"] not in allowed
    oracle = read_oracle(CASES / "regression/r01/bundle.json")
    assert next(line for line in oracle.lines if line.line_id == "D2").valid_cents == 0


def test_unsigned_pod_and_late_damage_are_honest_missing_information_cases():
    unsigned = read_bundle(CASES / "regression/r03/bundle.json")
    assert by_ref(unsigned, "POD").fields["signed"] is False
    late = read_bundle(CASES / "regression/r04/bundle.json")
    terms = by_ref(late, "TERMS").fields
    assert "damage_late_waived" not in terms
    reported = date.fromisoformat(by_ref(late, "REM").fields["ded.1.reported_date"])
    delivered = date.fromisoformat(by_ref(late, "POD").fields["delivered_date"])
    assert (reported - delivered).days > terms["damage_window_days"]
    for case_id in ("r03", "r04"):
        oracle = read_oracle(CASES / "regression" / case_id / "bundle.json")
        assert oracle.lines[0].verdict == "needs_info"
        assert {proposal.kind for proposal in oracle.proposals} == {ProposalKind.info_request}


def test_nonpayment_claim_items_use_fixed_ids_and_restrict_limit():
    path = CASES / "regression/r07/bundle.json"
    bundle, oracle = read_bundle(path), read_oracle(path)
    assert not any(
        doc.kind in {DocKind.payment, DocKind.remittance, DocKind.debit_memo} for doc in bundle.docs
    )
    terms = by_ref(bundle, "P-B").fields
    assert by_ref(bundle, "INV").fields["total_cents"] > terms["credit_limit_cents"]
    assert oracle.claim_items["claim.credit_limit"] == "restricted"
    assert oracle.claim_items["claim.disputed_portion"] == "present"
    assert set(oracle.claim_items) == {
        "claim.notice_receipt",
        "claim.waiting_period",
        "claim.doc.1",
        "claim.doc.2",
        "claim.doc.3",
        "claim.doc.4",
        "claim.collection_history",
        "claim.disputed_portion",
        "claim.credit_limit",
    }
    due = date.fromisoformat(by_ref(bundle, "INV").fields["due_date"])
    assert oracle.notice_deadline == due + timedelta(
        days=terms["mep_days_after_due"] + terms["notice_days_after_mep"]
    )


@pytest.fixture
def fixture_world():
    # Deferred provider import keeps the schema tests independently collectible (r10 §4).
    from recoup.contracts.testing import PassValidator, TextOnlyIngestor
    from recoup.world.store import SqliteWorld

    world = SqliteWorld(":memory:", TextOnlyIngestor(), PassValidator())
    try:
        yield world
    finally:
        world.db.close()


@pytest.mark.parametrize("path", BUNDLES, ids=lambda p: str(p.relative_to(CASES)))
def test_real_loader_preserves_fixture_balances_lines_and_quarantine(path, fixture_world):
    from recoup.contracts.interfaces import GateError

    bundle = read_bundle(path)
    result = fixture_world.load_bundle(bundle, str(path.parent))
    if bundle.currency != "USD":
        assert result.status == "quarantined"
        records = fixture_world.list_quarantined()
        assert len(records) == 1 and records[0].case_id == bundle.case_id
        assert "EUR" in records[0].reason
        assert CaseBundle.model_validate_json(records[0].raw_bundle_json) == bundle
        assert fixture_world.list_cases() == []
        assert fixture_world.db.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0
        assert fixture_world.db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
        with pytest.raises(GateError):
            fixture_world.view(bundle.case_id)
        return
    assert result.status == "loaded"
    view = fixture_world.view(bundle.case_id)
    invoice = by_ref(bundle, "INV")
    assert view.invoice_total.cents == invoice.fields["total_cents"]
    paid = sum(doc.fields["paid_cents"] for doc in bundle.docs if doc.kind == DocKind.payment)
    assert view.open_balance.cents == view.invoice_total.cents - paid
    assert view.provenance == "synthetic"
    evidence = fixture_world.active_evidence(bundle.case_id)
    assert {doc.doc_ref for doc in evidence} == {doc.doc_ref for doc in bundle.docs}
    assert all(doc.readable for doc in evidence)
    for source in bundle.docs:
        loaded = next(doc for doc in evidence if doc.doc_ref == source.doc_ref)
        assert loaded.fields == source.fields and loaded.text == source.text
    lines = fixture_world.deduction_lines(bundle.case_id)
    assert sum(line.claimed.cents for line in lines) == view.open_balance.cents
    if path in REGRESSIONS:
        oracle = read_oracle(path)
        assert {line.line_id for line in lines} == {line.line_id for line in oracle.lines}
    else:
        expected = {"H": {"D1": 312000, "D2": 312000}, "C": {"D1": 50000}, "N": {"U1": 215000}}
        assert {line.line_id: line.claimed.cents for line in lines} == expected[bundle.case_id]
    basis = fixture_world.fact_set(bundle.case_id)
    assert basis.basis_hash == fixture_world.evidence_set_hash(bundle.case_id)
    assert len(basis.docs) == len(bundle.docs)


def test_real_loader_hero_next_due_keeps_future_documents_held(fixture_world):
    bundle = read_bundle(CASES / "demo/H/bundle.json")
    fixture_world.load_bundle(bundle)
    assert fixture_world.next_due_day() == 3
    active = fixture_world.active_evidence("H")
    assert next(doc for doc in active if doc.doc_ref == "POD").version == 1
    assert all(doc.doc_ref != "INSPECTION" for doc in active)
    original_hash = fixture_world.evidence_set_hash("H")
    fixture_world.advance_to(3, release_events=False)
    assert fixture_world.clock.day() == 3
    assert fixture_world.evidence_set_hash("H") == original_hash
    assert fixture_world.next_due_day() == 3
