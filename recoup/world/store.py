"""SQLite World core; business rules are defined in design/02 §3–4."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import GateError, Ingestor, ProposalValidator
from recoup.contracts.models import (
    ActionAttempt,
    Approval,
    CaseHistory,
    CaseStatus,
    CaseView,
    Citation,
    Decision,
    DeductionReason,
    DocStatus,
    DomainEvent,
    DueWork,
    EffectiveFact,
    Evidence,
    FactRevision,
    FactSet,
    FieldTrust,
    GateIssue,
    InsuranceStatus,
    LedgerEntry,
    LineAmount,
    LineReasonRevision,
    LoadResult,
    Proposal,
    ProposalStatus,
    QuarantineRecord,
    Readiness,
    Receipt,
    Scalar,
    Target,
    TraceEvent,
)
from recoup.contracts.money import Money
from recoup.contracts.resolve import resolve_citation

from .clock import SimClock
from .hashing import basis_hash as compute_basis_hash
from .hashing import content_hash, digest
from .ids import new_id
from .ledger import balance, cents
from .lines import deduction_lines

_MODELS = {
    "quarantine": QuarantineRecord,
    "evidence": Evidence,
    "facts": FactRevision,
    "line_reasons": LineReasonRevision,
    "ledger": LedgerEntry,
    "decisions": Decision,
    "readiness": Readiness,
    "proposals": Proposal,
    "approvals": Approval,
    "receipts": Receipt,
    "due_work": DueWork,
    "events": DomainEvent,
    "traces": TraceEvent,
    "attempts": ActionAttempt,
}


class SqliteWorld:
    def __init__(self, path: str, ingestor: Ingestor, validator: ProposalValidator) -> None:
        if path != ":memory:":
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(
            str(Path(path).expanduser()) if path != ":memory:" else path, isolation_level=None
        )
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.ingestor, self.validator = ingestor, validator
        self._depth = 0
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                insurance TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                doc_ref TEXT NOT NULL,
                version INTEGER NOT NULL,
                data TEXT NOT NULL,
                UNIQUE(case_id,doc_ref,version));
            CREATE TABLE IF NOT EXISTS proposals (
                id TEXT NOT NULL,
                version INTEGER NOT NULL,
                case_id TEXT NOT NULL,
                business_key TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY(id,version));
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                business_key TEXT UNIQUE NOT NULL,
                idempotency_key TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS due_work (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                idempotency_key TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS held_docs (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                day INTEGER NOT NULL,
                system TEXT,
                bundle_dir TEXT,
                data TEXT NOT NULL,
                released INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS basis_members (
                hash TEXT NOT NULL,
                member TEXT NOT NULL,
                PRIMARY KEY(hash,member));
            CREATE TABLE IF NOT EXISTS bases (
                case_id TEXT NOT NULL,
                hash TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY(case_id,hash));
            CREATE TABLE IF NOT EXISTS lines (
                id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                data TEXT NOT NULL,
                PRIMARY KEY(case_id,id));
        """)
        for table in _MODELS.keys() - {"evidence", "proposals", "receipts", "due_work", "events"}:
            self.db.execute(
                f"CREATE TABLE IF NOT EXISTS {table} "
                "(id TEXT PRIMARY KEY, case_id TEXT NOT NULL, data TEXT NOT NULL)"
            )
        self.clock = SimClock(self.db)

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        name = f"world_{self._depth}"
        self.db.execute(f"SAVEPOINT {name}")
        self._depth += 1
        try:
            yield
        except BaseException:
            self.db.execute(f"ROLLBACK TO SAVEPOINT {name}")
            self.db.execute(f"RELEASE SAVEPOINT {name}")
            raise
        else:
            self.db.execute(f"RELEASE SAVEPOINT {name}")
        finally:
            self._depth -= 1

    @staticmethod
    def _error(code: str, message: str) -> None:
        raise GateError([GateIssue(code=code, message=message)])

    def _case(self, case_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if row is None:
            self._error("unknown_case", case_id)
        return row

    def _rows(self, table: str, case_id: str | None = None) -> list:
        sql = f"SELECT data FROM {table}"
        params = ()
        if case_id is not None:
            sql += " WHERE case_id=?"
            params = (case_id,)
        sql += " ORDER BY " + ("seq" if table == "events" else "rowid")
        return [_MODELS[table].model_validate_json(row[0]) for row in self.db.execute(sql, params)]

    def _save(
        self, table: str, item, identity: str, case_id: str, *, replace: bool = False
    ) -> None:
        verb = "INSERT OR REPLACE" if replace else "INSERT"
        self.db.execute(
            f"{verb} INTO {table}(id,case_id,data) VALUES(?,?,?)",
            (identity, case_id, item.model_dump_json()),
        )

    def _proposal(self, proposal_id: str, version: int) -> Proposal:
        row = self.db.execute(
            "SELECT data FROM proposals WHERE id=? AND version=?", (proposal_id, version)
        ).fetchone()
        if row is None:
            self._error("unknown_proposal", f"{proposal_id}:{version}")
        return Proposal.model_validate_json(row[0])

    def _write_proposal(self, p: Proposal) -> None:
        self.db.execute(
            "INSERT INTO proposals(id,version,case_id,business_key,data) VALUES(?,?,?,?,?) "
            "ON CONFLICT(id,version) DO UPDATE SET data=excluded.data",
            (p.proposal_id, p.version, p.case_id, p.business_key, p.model_dump_json()),
        )

    def _event(self, case_id: str, kind: str, ref: str) -> DomainEvent:
        event = DomainEvent(
            event_id=new_id("EV"), case_id=case_id, seq=0, at=self.clock.now(), type=kind, ref=ref
        )
        cursor = self.db.execute(
            "INSERT INTO events(id,case_id,data) VALUES(?,?,?)",
            (event.event_id, case_id, event.model_dump_json()),
        )
        event.seq = cursor.lastrowid
        self.db.execute(
            "UPDATE events SET data=? WHERE id=?", (event.model_dump_json(), event.event_id)
        )
        return event

    def load_bundle(self, bundle: CaseBundle, bundle_dir: str | None = None) -> LoadResult:
        with self.transaction():
            if bundle.currency != "USD":
                q = QuarantineRecord(
                    case_id=bundle.case_id,
                    reason=f"Unsupported currency: {bundle.currency}",
                    raw_bundle_json=bundle.model_dump_json(),
                    at=self.clock.now(),
                )
                self._save("quarantine", q, bundle.case_id, bundle.case_id, replace=True)
                return LoadResult(case_id=bundle.case_id, status="quarantined", reason=q.reason)
            previous = self.db.execute(
                "SELECT data FROM cases WHERE id=?", (bundle.case_id,)
            ).fetchone()
            if previous:
                if previous[0] == bundle.model_dump_json():
                    return LoadResult(case_id=bundle.case_id, status="loaded")
                self._error("case_exists", bundle.case_id)
            start = self.db.execute("SELECT value FROM meta WHERE key='start_date'").fetchone()
            if start and start[0] != bundle.start_date.isoformat():
                self._error("clock_mismatch", "All bundles must share the simulated start date")
            self.db.execute(
                "INSERT OR IGNORE INTO meta VALUES('start_date',?)",
                (bundle.start_date.isoformat(),),
            )
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('sim_day','0')")
            insurance = InsuranceStatus.watching if bundle.policy_ref else InsuranceStatus.none
            self.db.execute(
                "INSERT INTO cases(id,data,status,insurance) VALUES(?,?,?,?)",
                (bundle.case_id, bundle.model_dump_json(), CaseStatus.open.value, insurance.value),
            )
            for doc in bundle.docs:
                if doc.held_by or doc.available_at_day > self.clock.day():
                    self._hold(bundle.case_id, doc, doc.available_at_day, bundle_dir)
                else:
                    self.add_evidence(bundle.case_id, doc, bundle_dir)
            for event in bundle.events:
                self._hold(bundle.case_id, event.doc, event.at_day, bundle_dir)
            self._event(bundle.case_id, "case_loaded", bundle.case_id)
            self.fact_set(bundle.case_id)
            return LoadResult(case_id=bundle.case_id, status="loaded")

    def _hold(self, case_id: str, doc: BundleDoc, day: int, bundle_dir: str | None) -> None:
        self.db.execute(
            "INSERT INTO held_docs(id,case_id,day,system,bundle_dir,data) VALUES(?,?,?,?,?,?)",
            (new_id("HELD"), case_id, day, doc.held_by, bundle_dir, doc.model_dump_json()),
        )

    def list_quarantined(self) -> list[QuarantineRecord]:
        return self._rows("quarantine")

    def add_evidence(
        self, case_id: str, doc: BundleDoc, bundle_dir: str | None = None
    ) -> Evidence | None:
        with self.transaction():
            self._case(case_id)
            if doc.version < 1:
                raise ValueError("Evidence version must be positive")
            output = self.ingestor.ingest(doc, bundle_dir)
            sha = content_hash(output.text, output.fields)
            prior = self.db.execute(
                "SELECT data FROM evidence WHERE case_id=? AND doc_ref=? AND version=?",
                (case_id, doc.doc_ref, doc.version),
            ).fetchone()
            if prior:
                old = Evidence.model_validate_json(prior[0])
                if old.content_sha256 == sha:
                    self._event(case_id, "duplicate_ignored", old.evidence_id)
                    return None
                self.set_status(
                    case_id, status=CaseStatus.needs_human, reason="conflicting redelivery"
                )
                return None
            self.fact_set(case_id)
            row = Evidence(
                evidence_id=f"EV-{case_id}-{doc.doc_ref}-v{doc.version}",
                case_id=case_id,
                doc_ref=doc.doc_ref,
                version=doc.version,
                kind=doc.kind,
                title=doc.title,
                available_from=self.clock.at_day(doc.available_at_day),
                content_sha256=sha,
                readable=output.readable,
                method=output.method,
                failure=output.failure,
                text=output.text,
                fields=output.fields,
                field_trust=output.field_trust,
                active=False,
            )
            old_active = next(
                (e for e in self.active_evidence(case_id) if e.doc_ref == doc.doc_ref), None
            )
            self.db.execute(
                "INSERT INTO evidence(id,case_id,doc_ref,version,data) VALUES(?,?,?,?,?)",
                (row.evidence_id, case_id, row.doc_ref, row.version, row.model_dump_json()),
            )
            current = self.evidence(row.evidence_id)
            if current.active:
                self._intake_ledger(current)
                self._event(
                    case_id,
                    "evidence_superseded" if old_active else "evidence_added",
                    row.evidence_id,
                )
            self.fact_set(case_id)
            return current

    def _intake_ledger(self, row: Evidence) -> None:
        # A document identity seeds the mock ledger once; corrections are not reposts.
        if any(e.source == row.doc_ref for e in self.ledger(row.case_id)):
            return
        kind_key = {
            "invoice": ("invoice", "total_cents"),
            "payment": ("payment", "paid_cents"),
            "credit_memo": ("credit_posted", "amount_cents"),
        }.get(row.kind)
        if kind_key is None:
            return
        kind, key = kind_key
        if key not in row.fields:
            return
        entry = LedgerEntry(
            entry_id=new_id("L"),
            case_id=row.case_id,
            kind=kind,
            amount=Money(cents=cents(row.fields, key)),
            line_id=row.fields.get("line_id"),
            source=row.doc_ref,
            at=self.clock.now(),
        )
        self._save("ledger", entry, entry.entry_id, row.case_id)

    def _evidence_rows(self, case_id: str) -> list[Evidence]:
        rows = self._rows("evidence", case_id)
        newest: dict[str, Evidence] = {}
        for row in rows:
            if row.available_from <= self.clock.now() and (
                row.doc_ref not in newest or row.version > newest[row.doc_ref].version
            ):
                newest[row.doc_ref] = row
        return [
            row.model_copy(
                update={
                    "active": newest.get(row.doc_ref) is row,
                    "superseded_by": newest[row.doc_ref].evidence_id
                    if row.doc_ref in newest and newest[row.doc_ref].version > row.version
                    else None,
                }
            )
            for row in rows
        ]

    def active_evidence(self, case_id: str) -> list[Evidence]:
        self._case(case_id)
        return [row for row in self._evidence_rows(case_id) if row.active]

    def evidence(self, evidence_id: str) -> Evidence:
        row = self.db.execute("SELECT case_id FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        if row is None:
            self._error("unknown_evidence", evidence_id)
        return next(e for e in self._evidence_rows(row[0]) if e.evidence_id == evidence_id)

    def _latest_facts(self, case_id: str) -> dict[tuple[str, str], FactRevision]:
        return {(f.evidence_id, f.key): f for f in self._rows("facts", case_id)}

    def _latest_reasons(self, case_id: str) -> list[LineReasonRevision]:
        return list({r.line_id: r for r in self._rows("line_reasons", case_id)}.values())

    def add_fact(
        self,
        evidence_id: str,
        key: str,
        value: Scalar,
        trust: FieldTrust,
        citation: Citation | None,
        by: str,
    ) -> FactRevision:
        with self.transaction():
            row = self.evidence(evidence_id)
            if not row.active:
                self._error("superseded_citation", evidence_id)
            if citation is not None:
                if citation.evidence_id != evidence_id:
                    self._error("invalid_citation", "Fact citation must reference its own evidence")
                self.resolve_citation(citation)
            old = self._latest_facts(row.case_id).get((evidence_id, key))
            if (
                old
                and (old.value, old.trust, old.citation) == (value, trust, citation)
                and type(old.value) is type(value)
            ):
                return old
            self.fact_set(row.case_id)
            fact = FactRevision(
                fact_id=new_id("F"),
                case_id=row.case_id,
                evidence_id=evidence_id,
                key=key,
                value=value,
                trust=trust,
                citation=citation,
                supersedes_fact_id=old.fact_id if old else None,
                at=self.clock.now(),
                by=by,
            )
            self._save("facts", fact, fact.fact_id, row.case_id)
            self.fact_set(row.case_id)
            return fact

    def confirm_field(self, evidence_id: str, key: str, approver: str) -> FactRevision:
        row = self.evidence(evidence_id)
        old = self._latest_facts(row.case_id).get((evidence_id, key))
        if old:
            return self.add_fact(
                evidence_id, key, old.value, FieldTrust.human_confirmed, old.citation, approver
            )
        if key not in row.fields:
            self._error("unknown_field", key)
        return self.add_fact(
            evidence_id,
            key,
            row.fields[key],
            FieldTrust.human_confirmed,
            Citation(
                evidence_id=evidence_id,
                locator=f"fields.{key}",
                quote=self._render(row.fields[key]),
            ),
            approver,
        )

    def set_line_reason(
        self,
        case_id: str,
        line_id: str,
        reason: DeductionReason,
        trust: FieldTrust,
        citation: Citation | None,
    ) -> LineReasonRevision:
        with self.transaction():
            if not any(line.line_id == line_id for line in self.deduction_lines(case_id)):
                self._error("unknown_line", line_id)
            if citation:
                self.resolve_citation(citation)
                if self.evidence(citation.evidence_id).case_id != case_id:
                    self._error("invalid_citation", "Cross-case line reason")
            old = next((r for r in self._latest_reasons(case_id) if r.line_id == line_id), None)
            if old and (old.reason, old.trust, old.citation) == (reason, trust, citation):
                return old
            self.fact_set(case_id)
            revision = LineReasonRevision(
                case_id=case_id,
                line_id=line_id,
                reason=reason,
                trust=trust,
                citation=citation,
                at=self.clock.now(),
            )
            self._save("line_reasons", revision, new_id("R"), case_id)
            self.fact_set(case_id)
            return revision

    @staticmethod
    def _render(value: Scalar) -> str:
        return str(value).lower() if isinstance(value, bool) else str(value)

    def fact_set(self, case_id: str, basis_hash: str | None = None) -> FactSet:
        self._case(case_id)
        if basis_hash is not None:
            row = self.db.execute(
                "SELECT data FROM bases WHERE case_id=? AND hash=?", (case_id, basis_hash)
            ).fetchone()
            if row is None:
                self._error("unknown_basis", basis_hash)
            return FactSet.model_validate_json(row[0])
        active = self.active_evidence(case_id)
        latest = self._latest_facts(case_id)
        facts = []
        members = []
        for row in active:
            members.append(f"E:{row.evidence_id}:{row.content_sha256}")
            revisions = {
                key: revision for (eid, key), revision in latest.items() if eid == row.evidence_id
            }
            for key in sorted(row.fields.keys() | revisions.keys()):
                revision = revisions.get(key)
                value = revision.value if revision else row.fields[key]
                facts.append(
                    EffectiveFact(
                        evidence_id=row.evidence_id,
                        doc_kind=row.kind,
                        doc_ref=row.doc_ref,
                        key=key,
                        value=value,
                        trust=revision.trust
                        if revision
                        else row.field_trust.get(key, FieldTrust.source),
                        origin="fact" if revision else "source",
                        fact_id=revision.fact_id if revision else None,
                        citation=Citation(
                            evidence_id=row.evidence_id,
                            locator=f"fact:{revision.fact_id}" if revision else f"fields.{key}",
                            quote=self._render(value),
                        ),
                    )
                )
                if revision:
                    members.append(f"F:{revision.fact_id}")
        members.extend(
            f"R:{r.line_id}:{r.reason.value}:{r.trust.value}" for r in self._latest_reasons(case_id)
        )
        hashed = compute_basis_hash(members)
        result = FactSet(
            case_id=case_id,
            basis_hash=hashed,
            facts=facts,
            docs=[
                DocStatus(
                    evidence_id=e.evidence_id,
                    doc_ref=e.doc_ref,
                    kind=e.kind,
                    readable=e.readable,
                    failure=e.failure,
                )
                for e in active
            ],
        )
        self.db.execute(
            "INSERT OR IGNORE INTO bases(case_id,hash,data) VALUES(?,?,?)",
            (case_id, hashed, result.model_dump_json()),
        )
        self.db.executemany(
            "INSERT OR IGNORE INTO basis_members(hash,member) VALUES(?,?)",
            [(hashed, member) for member in members],
        )
        return result

    def evidence_set_hash(self, case_id: str) -> str:
        return self.fact_set(case_id).basis_hash

    def resolve_citation(self, c: Citation, basis_hash: str | None = None) -> Scalar | str | None:
        row = self.evidence(c.evidence_id)
        return resolve_citation(
            c,
            self.fact_set(row.case_id, basis_hash),
            self._evidence_rows(row.case_id),
            self._rows("facts", row.case_id),
        )

    def ledger(self, case_id: str) -> list[LedgerEntry]:
        self._case(case_id)
        return self._rows("ledger", case_id)

    def ledger_balance(self, case_id: str) -> Money:
        return balance(self.ledger(case_id))

    def deduction_lines(self, case_id: str):
        effective = self.fact_set(case_id)
        docs = []
        for row in self.active_evidence(case_id):
            fields = {
                fact.key: fact.value
                for fact in effective.facts
                if fact.evidence_id == row.evidence_id
            }
            trust = {
                fact.key: fact.trust
                for fact in effective.facts
                if fact.evidence_id == row.evidence_id
            }
            docs.append(row.model_copy(update={"fields": fields, "field_trust": trust}))
        return deduction_lines(
            docs,
            self.ledger(case_id),
            self.clock.now().date(),
            self._latest_reasons(case_id),
        )

    def allowed_recipients(self, case_id: str, target: Target) -> list[str]:
        return (
            CaseBundle.model_validate_json(self._case(case_id)["data"])
            .allowed_recipients.get(target.value, [])
            .copy()
        )

    def current_decision(self, case_id: str) -> Decision | None:
        self._case(case_id)
        return next((d for d in reversed(self._rows("decisions", case_id)) if d.current), None)

    def save_decision(self, d: Decision) -> Decision:
        with self.transaction():
            if d.evidence_set_hash != self.evidence_set_hash(d.case_id):
                self._error("stale_decision", "Decision basis is not current")
            previous = self._rows("decisions", d.case_id)
            for old in previous:
                if old.current:
                    self._save(
                        "decisions",
                        old.model_copy(update={"current": False}),
                        old.decision_id,
                        d.case_id,
                        replace=True,
                    )
            saved = d.model_copy(
                update={
                    "decision_id": new_id("D")
                    if any(old.decision_id == d.decision_id for old in previous)
                    else d.decision_id,
                    "version": max((old.version for old in previous), default=0) + 1,
                    "current": True,
                }
            )
            self._save("decisions", saved, saved.decision_id, saved.case_id)
            return saved

    def readiness(self, case_id: str) -> list[Readiness]:
        self._case(case_id)
        return self._rows("readiness", case_id)

    def save_readiness(self, r: Readiness) -> Readiness:
        if r.evidence_set_hash != self.evidence_set_hash(r.case_id):
            self._error("stale_readiness", "Readiness basis is not current")
        self._save("readiness", r, r.readiness_id, r.case_id, replace=True)
        return r

    def _void_approvals(self, p: Proposal, reason: str) -> None:
        for approval in self._rows("approvals", p.case_id):
            if (
                approval.proposal_id == p.proposal_id
                and approval.proposal_version == p.version
                and not approval.void
            ):
                self._save(
                    "approvals",
                    approval.model_copy(update={"void": True, "void_reason": reason}),
                    approval.approval_id,
                    p.case_id,
                    replace=True,
                )

    def save_proposal(self, p: Proposal) -> Proposal:
        with self.transaction():
            self._case(p.case_id)
            if any(r.business_key == p.business_key for r in self._rows("receipts", p.case_id)):
                self._error("already_submitted", p.business_key)
            previous = [
                old
                for old in self._rows("proposals", p.case_id)
                if old.business_key == p.business_key
            ]
            if self.db.execute(
                "SELECT 1 FROM proposals WHERE id=? AND business_key<>?",
                (p.proposal_id, p.business_key),
            ).fetchone():
                self._error("proposal_identity", "Proposal id belongs to another business key")
            sha = digest(p.draft_text)
            candidate = p.model_copy(update={"draft_sha256": sha})
            for old in reversed(previous):
                if old.status in {ProposalStatus.proposed, ProposalStatus.approved} and (
                    old.draft_sha256,
                    old.allocations,
                    old.recipient,
                    old.evidence_set_hash,
                ) == (sha, p.allocations, p.recipient, p.evidence_set_hash):
                    return old
            issues = self.validator.validate(self, candidate, "save")
            if issues:
                raise GateError(issues)
            for old in previous:
                if old.status in {ProposalStatus.proposed, ProposalStatus.approved}:
                    self._write_proposal(old.model_copy(update={"status": ProposalStatus.stale}))
                    self._void_approvals(old, "proposal changed")
            candidate = candidate.model_copy(
                update={
                    "proposal_id": previous[0].proposal_id if previous else p.proposal_id,
                    "version": max((old.version for old in previous), default=0) + 1,
                    "status": ProposalStatus.proposed,
                }
            )
            self._write_proposal(candidate)
            return candidate

    def edit_proposal(
        self,
        proposal_id: str,
        version: int,
        *,
        draft_text: str | None = None,
        recipient: str | None = None,
        allocations: list[LineAmount] | None = None,
        editor: str = "user",
    ) -> Proposal:
        with self.transaction():
            old = self._proposal(proposal_id, version)
            if old.status != ProposalStatus.proposed:
                self._error("immutable_proposal", "Only a proposed version can be edited")
            amounts = allocations if allocations is not None else old.allocations
            limits = {a.line_id: a.amount.cents for a in old.allocations}
            if len({a.line_id for a in amounts}) != len(amounts) or any(
                a.line_id not in limits or not 0 <= a.amount.cents <= limits[a.line_id]
                for a in amounts
            ):
                self._error("allocation_increase", "Edits may only decrease existing line amounts")
            selected = recipient if recipient is not None else old.recipient
            if selected not in self.allowed_recipients(old.case_id, old.target):
                self._error("recipient_not_allowed", selected)
            edited = old.model_copy(
                update={
                    "draft_text": old.draft_text if draft_text is None else draft_text,
                    "recipient": selected,
                    "allocations": amounts,
                    "amount": Money(cents=sum(a.amount.cents for a in amounts))
                    if old.amount is not None
                    else None,
                    "created_by": "human_edit",
                    "created_at": self.clock.now(),
                }
            )
            result = self.save_proposal(edited)
            self.trace(
                TraceEvent(
                    run_id=editor,
                    case_id=old.case_id,
                    step=0,
                    sim_time=self.clock.now(),
                    kind="state",
                    result_summary="proposal edited",
                    args={
                        "before": old.model_dump(mode="json"),
                        "after": result.model_dump(mode="json"),
                    },
                )
            )
            return result

    def approve(self, proposal_id: str, version: int, approver: str) -> Approval:
        with self.transaction():
            p = self._proposal(proposal_id, version)
            if p.status != ProposalStatus.proposed:
                self._error("not_proposed", "Proposal is not awaiting approval")
            issues = self.validator.validate(self, p, "approve")
            if issues:
                raise GateError(issues)
            approval = self._approval(p, approver, True, "")
            self._write_proposal(p.model_copy(update={"status": ProposalStatus.approved}))
            return approval

    def _approval(self, p: Proposal, approver: str, approved: bool, reason: str) -> Approval:
        approval = Approval(
            approval_id=new_id("A"),
            proposal_id=p.proposal_id,
            proposal_version=p.version,
            recipient=p.recipient,
            amount=p.amount,
            draft_sha256=p.draft_sha256,
            evidence_set_hash=p.evidence_set_hash,
            decision_version=p.decision_version,
            approver=approver,
            approved=approved,
            reason=reason,
            at=self.clock.now(),
        )
        self._save("approvals", approval, approval.approval_id, p.case_id)
        return approval

    def reject(self, proposal_id: str, version: int, approver: str, reason: str) -> Approval:
        with self.transaction():
            if not reason.strip():
                self._error("reason_required", "Rejection needs a reason")
            p = self._proposal(proposal_id, version)
            if p.status not in {ProposalStatus.proposed, ProposalStatus.approved}:
                self._error("not_proposed", "Proposal cannot be rejected")
            self._void_approvals(p, "rejected")
            approval = self._approval(p, approver, False, reason)
            self._write_proposal(p.model_copy(update={"status": ProposalStatus.rejected}))
            return approval

    def set_status(
        self,
        case_id: str,
        status: CaseStatus | None = None,
        insurance: InsuranceStatus | None = None,
        reason: str = "",
    ) -> None:
        row = self._case(case_id)
        self.db.execute(
            "UPDATE cases SET status=?,insurance=?,reason=? WHERE id=?",
            (
                status.value if status else row["status"],
                insurance.value if insurance else row["insurance"],
                reason,
                case_id,
            ),
        )

    def view(self, case_id: str) -> CaseView:
        row = self._case(case_id)
        bundle = CaseBundle.model_validate_json(row["data"])
        proposals = self._rows("proposals", case_id)
        latest = {p.proposal_id: p for p in proposals}
        return CaseView(
            case_id=case_id,
            title=bundle.title,
            buyer=bundle.buyer,
            status=row["status"],
            status_reason=row["reason"],
            insurance=row["insurance"],
            sim_day=self.clock.day(),
            sim_now=self.clock.now(),
            invoice_total=Money(
                cents=sum(e.amount.cents for e in self.ledger(case_id) if e.kind == "invoice")
            ),
            open_balance=self.ledger_balance(case_id),
            lines=self.deduction_lines(case_id),
            decision=self.current_decision(case_id),
            proposals=list(latest.values()),
            receipts=self._rows("receipts", case_id),
            readiness=self.readiness(case_id),
            due=[w for w in self._rows("due_work", case_id) if w.status == "pending"],
            evidence=self.active_evidence(case_id),
        )

    def list_cases(self) -> list[CaseView]:
        return [self.view(row[0]) for row in self.db.execute("SELECT id FROM cases ORDER BY rowid")]

    def history(self, case_id: str) -> CaseHistory:
        self._case(case_id)
        return CaseHistory(
            case_id=case_id,
            evidence_all=self._evidence_rows(case_id),
            facts=self._rows("facts", case_id),
            reasons=self._rows("line_reasons", case_id),
            decisions=self._rows("decisions", case_id),
            proposals_all=self._rows("proposals", case_id),
            approvals=self._rows("approvals", case_id),
            receipts=self._rows("receipts", case_id),
            attempts=self._rows("attempts", case_id),
            ledger=self.ledger(case_id),
            events=self._rows("events", case_id),
            traces=self._rows("traces", case_id),
        )

    def advance_to(self, day: int, release_events: bool = True) -> list[DomainEvent]:
        if type(day) is not int or day < self.clock.day():
            raise ValueError("Cannot reverse the simulated clock")
        if release_events:
            self._error(
                "not_implemented", "Event release is implemented in 006-3; use release_events=False"
            )
        with self.transaction():
            self.db.execute(
                "INSERT INTO meta(key,value) VALUES('sim_day',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(day),),
            )
        return []

    def pending_events(self) -> list[DomainEvent]:
        return [event for event in self._rows("events") if not event.processed]

    def mark_event(self, event_id: str) -> None:
        row = self.db.execute("SELECT data FROM events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            self._error("unknown_event", event_id)
        event = DomainEvent.model_validate_json(row[0]).model_copy(update={"processed": True})
        self.db.execute("UPDATE events SET data=? WHERE id=?", (event.model_dump_json(), event_id))

    def schedule(self, w: DueWork) -> DueWork:
        self._case(w.case_id)
        row = self.db.execute(
            "SELECT data FROM due_work WHERE idempotency_key=?", (w.idempotency_key,)
        ).fetchone()
        if row:
            return DueWork.model_validate_json(row[0])
        self.db.execute(
            "INSERT INTO due_work(id,case_id,idempotency_key,data) VALUES(?,?,?,?)",
            (w.due_id, w.case_id, w.idempotency_key, w.model_dump_json()),
        )
        return w

    def due(self, until: datetime) -> list[DueWork]:
        return sorted(
            [w for w in self._rows("due_work") if w.status == "pending" and w.due_at <= until],
            key=lambda w: (w.due_at, w.due_id),
        )

    def mark_due(self, due_id: str, status: str) -> None:
        if status not in {"done", "cancelled"}:
            raise ValueError("Invalid due status")
        row = self.db.execute("SELECT data FROM due_work WHERE id=?", (due_id,)).fetchone()
        if row is None:
            self._error("unknown_due", due_id)
        work = DueWork.model_validate_json(row[0]).model_copy(update={"status": status})
        self.db.execute("UPDATE due_work SET data=? WHERE id=?", (work.model_dump_json(), due_id))

    def cancel_due(self, case_id: str, kind: str, reason: str) -> int:
        self._case(case_id)
        rows = [
            w for w in self._rows("due_work", case_id) if w.kind == kind and w.status == "pending"
        ]
        for work in rows:
            self.mark_due(work.due_id, "cancelled")
        return len(rows)

    def next_due_day(self) -> int | None:
        days = [
            (w.due_at.date() - self.clock.start_date()).days
            for w in self._rows("due_work")
            if w.status == "pending"
        ]
        days.extend(
            row[0]
            for row in self.db.execute(
                "SELECT day FROM held_docs WHERE released=0 AND (system IS NULL OR day>?)",
                (self.clock.day(),),
            )
        )
        return max(self.clock.day(), min(days)) if days else None

    def trace(self, e: TraceEvent) -> None:
        self._case(e.case_id)
        self._save("traces", e, new_id("T"), e.case_id)

    def record_attempt(self, a: ActionAttempt) -> None:
        self._case(a.case_id)
        self._save("attempts", a, a.attempt_id, a.case_id)

    def attach_held(self, case_id: str, system: str, query: str) -> list[Evidence]:
        self._error("not_implemented", "Held-document release is implemented in 006-3")

    def submit(self, proposal_id: str, version: int) -> Receipt:
        self._error("not_implemented", "Mock submission is implemented in 006-3")

    def fail_next(self, target: str) -> None:
        self._error("not_implemented", "Mock failures are implemented in 006-3")
