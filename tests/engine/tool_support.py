"""SYNTHETIC narrow tool-port support, never persistence/integration proof."""

from datetime import timedelta

from recoup.contracts.models import (
    CaseHistory,
    CaseView,
    Decision,
    ExtractMethod,
    FactRevision,
    LedgerEntry,
    LineDecision,
    Money,
    Receipt,
)
from recoup.contracts.resolve import resolve_citation
from recoup.engine.rules import run_rules

from .doubles import ScriptedClock
from .fixtures import NOW, fact_inputs, line_input, load_vectors


class ToolWorld:
    def __init__(self, facts, evidence, revisions, lines, ledger):
        self.clock = ScriptedClock(NOW)
        self.facts = facts
        self.inventory = evidence
        self.revisions = revisions
        self.entries = ledger
        self.traces = []
        self.added = []
        self.history_proposals = []
        total = sum(e.amount.cents for e in ledger if e.kind == "invoice")
        self.state = CaseView(
            case_id=facts.case_id,
            title="SYNTHETIC tools",
            buyer="SYNTHETIC buyer",
            status="open",
            insurance="none",
            sim_day=0,
            sim_now=NOW,
            invoice_total=Money(cents=total),
            open_balance=Money(cents=total),
            lines=lines,
            decision=None,
            proposals=[],
            receipts=[],
            readiness=[],
            due=[],
            evidence=evidence,
        )
        self.decide()

    def __getattr__(self, name):
        raise NotImplementedError(f"Unscripted World method: {name}")

    def _case(self, case_id):
        assert case_id == self.facts.case_id

    def fact_set(self, case_id, basis_hash=None):
        self._case(case_id)
        assert basis_hash is None or basis_hash == self.facts.basis_hash
        return self.facts.model_copy(deep=True)

    def view(self, case_id):
        self._case(case_id)
        return self.state.model_copy(deep=True)

    def history(self, case_id):
        self._case(case_id)
        return CaseHistory(
            case_id=case_id,
            evidence_all=self.inventory,
            facts=self.revisions,
            reasons=[],
            decisions=[self.state.decision] if self.state.decision else [],
            proposals_all=self.history_proposals,
            approvals=[],
            receipts=self.state.receipts,
            attempts=[],
            ledger=self.entries,
            events=[],
            traces=self.traces,
        )

    def current_decision(self, case_id):
        self._case(case_id)
        return self.state.decision

    def evidence_set_hash(self, case_id):
        self._case(case_id)
        return self.facts.basis_hash

    def active_evidence(self, case_id):
        self._case(case_id)
        return [e for e in self.inventory if e.active]

    def evidence(self, evidence_id):
        return next(e for e in self.inventory if e.evidence_id == evidence_id)

    def ledger(self, case_id):
        self._case(case_id)
        return self.entries.copy()

    def ledger_balance(self, case_id):
        self._case(case_id)
        return Money(
            cents=sum(e.amount.cents * (1 if e.kind == "invoice" else -1) for e in self.entries)
        )

    def allowed_recipients(self, case_id, target):
        self._case(case_id)
        assert target.value.startswith("mock_")
        return ["SYNTHETIC recipient"]

    def resolve_citation(self, c, basis_hash=None):
        assert basis_hash is None or basis_hash == self.facts.basis_hash
        return resolve_citation(c, self.facts, self.inventory, self.revisions)

    def add_fact(self, evidence_id, key, value, trust, citation, by):
        self.added.append((evidence_id, key, value, trust, citation, by))
        revision = FactRevision(
            fact_id=f"F-{len(self.added)}",
            case_id=self.facts.case_id,
            evidence_id=evidence_id,
            key=key,
            value=value,
            trust=trust,
            citation=citation,
            at=self.clock.now(),
            by=by,
        )
        self.revisions.append(revision)
        return revision

    def set_line_reason(self, case_id, line_id, reason, trust, citation):
        from recoup.contracts.models import LineReasonRevision

        self._case(case_id)
        return LineReasonRevision(
            case_id=case_id,
            line_id=line_id,
            reason=reason,
            trust=trust,
            citation=citation,
            at=self.clock.now(),
        )

    def save_decision(self, d):
        self.state.decision = d
        return d

    def save_readiness(self, r):
        self.state.readiness = [
            old for old in self.state.readiness if (old.kind, old.line_id) != (r.kind, r.line_id)
        ] + [r]
        return r

    def readiness(self, case_id):
        self._case(case_id)
        return self.state.readiness.copy()

    def save_proposal(self, p):
        self.history_proposals.append(p)
        self.state.proposals.append(p)
        return p

    def trace(self, e):
        self.traces.append(e)

    def schedule(self, w):
        self.state.due.append(w)
        return w

    def attach_held(self, case_id, system, query):
        self._case(case_id)
        assert (system, query) == ("erp", "SYNTHETIC missing")
        return []

    def set_status(self, case_id, status=None, insurance=None, reason=""):
        self._case(case_id)
        self.state.status = status or self.state.status
        self.state.status_reason = reason

    def decide(self):
        findings = run_rules(self.state.lines, self.facts, self.entries)
        old = self.state.decision
        self.state.decision = Decision(
            decision_id="D",
            case_id=self.facts.case_id,
            version=old.version + 1 if old else 1,
            evidence_set_hash=self.facts.basis_hash,
            current=True,
            model_id="fake",
            llm_mode="fake",
            prompt_version="v1",
            created_at=self.clock.now(),
            lines=[
                LineDecision(
                    line_id=f.line_id,
                    verdict=f.verdict,
                    basis=f.basis,
                    valid=f.valid,
                    disputed=f.disputed,
                    citations=f.citations,
                    rationale=f.note,
                )
                for f in findings
            ],
        )

    def record(self, proposal, number):
        """Install an explicit receipt fixture; this is not World.submit."""
        receipt = Receipt(
            receipt_id=f"MOCK-{number}",
            proposal_id=proposal.proposal_id,
            proposal_version=proposal.version,
            business_key=proposal.business_key,
            idempotency_key=f"I-{number}",
            target=proposal.target,
            amount=proposal.amount,
            allocations=proposal.allocations,
            corrects_receipt_id=proposal.corrects_receipt_id,
            at=NOW + timedelta(seconds=number),
        )
        self.state.receipts.append(receipt)
        if proposal.kind == "credit_memo":
            for allocation in proposal.allocations:
                self.entries.append(
                    LedgerEntry(
                        entry_id=f"L-{number}-{allocation.line_id}",
                        case_id=self.facts.case_id,
                        kind="credit_posted",
                        amount=allocation.amount,
                        line_id=allocation.line_id,
                        source=receipt.receipt_id,
                        at=receipt.at,
                    )
                )
        return receipt


def hero(after=False):
    vectors = {v["id"]: v for v in load_vectors("run_rules")}
    d1 = vectors["hero_d1_after_pod_v2" if after else "hero_d1_before_pod_v2"]["input"]
    d2 = vectors["hero_d2_before_pod_v2"]["input"]
    documents = d1["documents"]
    lines = [line_input(d1["line"]), line_input(d2["line"])]
    # Typed remittance facts used by the existing rule implementation.
    for i, line in enumerate(lines, 1):
        data = d1["line"] if i == 1 else d2["line"]
        fields = {
            f"ded.{i}.line_id": line.line_id,
            f"ded.{i}.reason": line.reason.value,
            f"ded.{i}.claimed_cents": line.claimed.cents,
        }
        if "ref" in data:
            fields[f"ded.{i}.ref"] = data["ref"]
        documents = documents + [{"id": f"remit-{i}", "kind": "remittance", "fields": fields}]
    facts, evidence, revisions = fact_inputs(documents, "SYNTHETIC-H")
    ledger = [
        LedgerEntry(
            entry_id=kind,
            case_id=facts.case_id,
            kind=kind,
            amount=Money(cents=value),
            line_id=None,
            source="SYNTHETIC",
            at=NOW,
        )
        for kind, value in [("invoice", 4800000), ("payment", 4176000)]
    ]
    return ToolWorld(facts, evidence, revisions, lines, ledger)


def text_world(text="SYNTHETIC received 360 cases; unit price $78.00.", kind="pod", method="text"):
    world = hero()
    facts, evidence, _ = fact_inputs(
        [{"id": "text-doc", "kind": kind, "fields": {}}], world.facts.case_id
    )
    doc = evidence[0].model_copy(update={"text": text, "method": ExtractMethod(method)})
    world.inventory.append(doc)
    world.facts.docs.extend(facts.docs)
    return world


def replace_basis(world, other):
    world.facts = other.facts
    world.inventory = other.inventory
    world.revisions = other.revisions
    world.state.evidence = other.inventory
    world.decide()
