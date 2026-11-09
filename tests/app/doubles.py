"""Narrow spies only; no persistence, financial validation or production World."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import EngineParts, GateError
from recoup.contracts.models import (
    Approval,
    CaseHistory,
    CaseView,
    DomainEvent,
    Evidence,
    FactRevision,
    GateIssue,
    LoadResult,
    Proposal,
    Receipt,
)
from recoup.contracts.money import Money
from recoup.contracts.testing import NullController, StubEngine, stub_parts

START = datetime(2026, 10, 20, tzinfo=timezone.utc)


def bundle(case_id="SYNTHETIC-A", currency="USD"):
    return CaseBundle(
        case_id=case_id,
        title="SYNTHETIC app unit fixture",
        seller="Synthetic seller",
        buyer="Synthetic buyer",
        currency=currency,
        invoice_ref="INV-UNIT",
        start_date=START.date(),
        docs=[],
    )


def document():
    return BundleDoc(doc_ref="POD", kind="pod", title="SYNTHETIC POD", text="Received")


class ClockSpy:
    def __init__(self):
        self.current_day = 0

    def day(self):
        return self.current_day

    def now(self):
        return START + timedelta(days=self.current_day)


class WorldSpy:
    def __init__(self):
        self.clock = ClockSpy()
        self.calls = []
        self.events = []
        self.day_events = {}
        self.failure = None
        self.duplicate = False
        self.evidence_row = Evidence(
            evidence_id="E-UNIT",
            case_id="SYNTHETIC-A",
            doc_ref="POD",
            version=1,
            kind="pod",
            title="SYNTHETIC POD",
            available_from=START,
            content_sha256="unit-hash",
            readable=True,
            method="text",
            text="Received",
            active=True,
        )
        self.fact = FactRevision(
            fact_id="F-UNIT",
            case_id="SYNTHETIC-A",
            evidence_id="E-UNIT",
            key="received",
            value=1,
            trust="human_confirmed",
            citation=None,
            at=START,
            by="user",
        )
        self.proposal = Proposal(
            proposal_id="P-UNIT",
            business_key="unit-message",
            version=2,
            case_id="SYNTHETIC-A",
            kind="info_request",
            target="mock_email",
            recipient="synthetic@example.test",
            amount=None,
            draft_text="Please provide the POD. SYNTHETIC / MOCK / LLM fake.",
            draft_sha256="unit-draft-hash",
            citations=[],
            decision_id=None,
            decision_version=None,
            evidence_set_hash="unit-basis",
            status="proposed",
            created_at=START,
            created_by="agent",
        )
        self.approval = Approval(
            approval_id="A-UNIT",
            proposal_id="P-UNIT",
            proposal_version=2,
            recipient=self.proposal.recipient,
            amount=None,
            draft_sha256=self.proposal.draft_sha256,
            evidence_set_hash=self.proposal.evidence_set_hash,
            decision_version=None,
            approver="user",
            approved=True,
            at=START,
        )
        self.receipt = Receipt(
            receipt_id="MOCK-UNIT",
            proposal_id="P-UNIT",
            proposal_version=2,
            business_key="unit-message",
            idempotency_key="unit-message-v2",
            target="mock_email",
            amount=None,
            at=START,
        )
        self.case_history = CaseHistory(
            case_id="SYNTHETIC-A",
            evidence_all=[self.evidence_row],
            facts=[self.fact],
            reasons=[],
            decisions=[],
            proposals_all=[self.proposal],
            approvals=[],
            receipts=[],
            attempts=[],
            ledger=[],
            events=[],
            traces=[],
        )

    def __getattr__(self, name):
        raise NotImplementedError(f"Unexpected WorldSpy operation: {name}")

    def _write(self, name, args, kwargs=None):
        self.calls.append((name, args, kwargs or {}))
        if self.failure == name:
            raise GateError([GateIssue(code="unit_rejected", message="SYNTHETIC rejection")])
        event = DomainEvent(
            event_id=f"EVENT-{len(self.calls)}",
            case_id="SYNTHETIC-A",
            seq=len(self.calls),
            at=self.clock.now(),
            type="case_loaded" if name == "load_bundle" else "evidence_added",
            ref="unit-ref",
        )
        self.events.append(event)

    def load_bundle(self, bundle, bundle_dir=None):
        self._write("load_bundle", (bundle, bundle_dir))
        return LoadResult(case_id=bundle.case_id, status="loaded")

    def add_evidence(self, case_id, doc, bundle_dir=None):
        self._write("add_evidence", (case_id, doc, bundle_dir))
        return None if self.duplicate else self.evidence_row

    def confirm_field(self, evidence_id, key, approver):
        self._write("confirm_field", (evidence_id, key, approver))
        return self.fact

    def edit_proposal(self, proposal_id, version, **changes):
        self._write("edit_proposal", (proposal_id, version), changes)
        return self.proposal

    def approve(self, proposal_id, version, approver):
        self._write("approve", (proposal_id, version, approver))
        return self.approval

    def reject(self, proposal_id, version, approver, reason):
        self._write("reject", (proposal_id, version, approver, reason))
        return self.approval.model_copy(update={"approved": False, "reason": reason})

    def submit(self, proposal_id, version):
        self._write("submit", (proposal_id, version))
        return self.receipt

    def pending_events(self):
        return list(self.events)

    def advance_to(self, day, release_events=True):
        assert day == self.clock.day() + 1
        assert release_events is True
        self.calls.append(("advance_to", (day,), {}))
        self.clock.current_day = day
        return self.day_events.get(day, [])

    def view(self, case_id):
        if case_id not in {"SYNTHETIC-A", "SYNTHETIC-B"}:
            raise KeyError(case_id)
        return CaseView(
            case_id=case_id,
            title="SYNTHETIC app unit fixture",
            buyer="Synthetic buyer",
            status="open",
            insurance="none",
            sim_day=self.clock.day(),
            sim_now=self.clock.now(),
            invoice_total=Money(cents=100),
            open_balance=Money(cents=100),
            lines=[],
            decision=None,
            proposals=[],
            receipts=[],
            readiness=[],
            due=[],
            evidence=[],
        )

    def list_cases(self):
        return [self.view(case_id) for case_id in ("SYNTHETIC-A", "SYNTHETIC-B")]

    def history(self, case_id):
        assert case_id == self.case_history.case_id
        return self.case_history

    def current_decision(self, case_id):
        return None

    def deduction_lines(self, case_id):
        return []


class ControllerSpy:
    def __init__(self, name):
        self.name = name
        self.calls = []

    @contextmanager
    def scope(self, case_ids):
        yield

    def react(self, world, events, run_id):
        self.calls.append((world, list(events), run_id, world.clock.day(), len(world.calls)))


class NullControllerSpy(NullController):
    def __init__(self):
        self.calls = []

    def react(self, world, events, run_id):
        self.calls.append((world, list(events), run_id, world.clock.day(), len(world.calls)))
        super().react(world, events, run_id)


class EngineSpy(StubEngine):
    def __init__(self):
        self.calls = []

    def investigate(self, world, case_id, llm, run_id):
        raise AssertionError("Facade must not call engine.investigate")

    def handle(self, world, llm, run_id):
        raise AssertionError("Facade must not call engine.handle")

    def static_output(self, world, case_id):
        self.calls.append(("static_output", world, case_id))
        return super().static_output(world, case_id)

    def rules_only(self, world, case_id):
        self.calls.append(("rules_only", world, case_id))
        return StubEngine.static_output(self, world, case_id)


class ToolsSpy:
    def __init__(self, tools):
        self.tools = tools
        self.calls = []

    def open(self, world, case_id, run_id, controller):
        self.calls.append((world, case_id, run_id, controller))
        return self.tools.open(world, case_id, run_id, controller)


def counted_parts():
    parts = stub_parts()
    return EngineParts(
        engine=EngineSpy(),
        ingestor=parts.ingestor,
        validator=parts.validator,
        tools=ToolsSpy(parts.tools),
    )
