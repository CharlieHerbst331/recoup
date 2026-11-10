"""SYNTHETIC 007-5 unit lane; no real persistence claims."""

from contextlib import contextmanager
from copy import deepcopy
from datetime import timedelta

import pytest

from recoup.contracts.models import DomainEvent, InsuranceStatus
from recoup.engine.derive import derive
from recoup.engine.gates import ProposalValidator
from recoup.engine.harness import HarnessEngine
from recoup.engine.llm import FakeLLM

from .fixtures import NOW, fact_inputs
from .test_harness_factory_ingest import insured_mixed
from .tool_support import ToolWorld, hero, replace_basis


class SchedulerWorld(ToolWorld):
    @classmethod
    def wrap(cls, source):
        world = cls.__new__(cls)
        world.__dict__ = deepcopy(source.__dict__)
        world.events = []
        world.fail_ack = False
        return world

    @contextmanager
    def transaction(self):
        snapshot = deepcopy(self.__dict__)
        try:
            yield
        except Exception:
            self.__dict__ = snapshot
            raise

    def event(self, kind, ref="", at=None):
        event = DomainEvent(
            event_id=f"E-{len(self.events)}",
            case_id=self.facts.case_id,
            seq=len(self.events),
            at=at or self.clock.now(),
            type=kind,
            ref=ref,
        )
        self.events.append(event)
        return event

    def pending_events(self):
        return [e for e in self.events if not e.processed]

    def mark_event(self, event_id):
        if self.fail_ack:
            raise RuntimeError("SYNTHETIC crash after proposal save")
        next(e for e in self.events if e.event_id == event_id).processed = True

    def due(self, until):
        return [w for w in self.state.due if w.status == "pending" and w.due_at <= until]

    def mark_due(self, due_id, status):
        next(w for w in self.state.due if w.due_id == due_id).status = status

    def cancel_due(self, case_id, kind, reason):
        items = [
            w
            for w in self.state.due
            if w.case_id == case_id and w.kind == kind and w.status == "pending"
        ]
        for w in items:
            w.status = "cancelled"
        return len(items)

    def schedule(self, w):
        old = next(
            (old for old in self.state.due if old.idempotency_key == w.idempotency_key), None
        )
        if old:
            return old
        return super().schedule(w)

    def save_proposal(self, p):
        old = next(
            (
                old
                for old in self.state.proposals
                if old.business_key == p.business_key
                and old.evidence_set_hash == p.evidence_set_hash
                and old.status != "stale"
            ),
            None,
        )
        return old or super().save_proposal(p)

    def set_status(self, case_id, status=None, insurance=None, reason=""):
        super().set_status(case_id, status, insurance, reason)
        if insurance:
            self.state.insurance = InsuranceStatus(insurance)

    def advance_to(self, day, release_events=True):
        self.clock.start = NOW
        self.clock.current_day = day
        return []


def handle(w, engine=None):
    return (engine or HarnessEngine()).handle(w, FakeLLM(), "SYNTHETIC-scheduler")


def outbound(w):
    p = next(p for p in derive(w, w.facts.case_id) if p.kind == "dispute")
    receipt = w.record(p, 1)
    w.event("receipt_issued", receipt.receipt_id, receipt.at)
    w.clock.start = receipt.at
    w.clock.current_day = 0
    return receipt


def add_email(w, sender="SYNTHETIC recipient"):
    _, evidence, _ = fact_inputs(
        [dict(id="reply", kind="email", fields={"from": sender})], w.facts.case_id
    )
    email = evidence[0].model_copy(update={"available_from": w.clock.now()})
    w.inventory.append(email)
    return w.event("evidence_added", email.evidence_id)


def test_day_three_correction_incremental_credit_no_repost():
    w = SchedulerWorld.wrap(hero())
    for n, p in enumerate(derive(w, w.facts.case_id), 1):
        w.record(p, n)
    replace_basis(w, hero(after=True))
    w.advance_to(3)
    w.event("evidence_superseded", w.inventory[0].evidence_id)
    handle(w)
    assert sorted((p.kind.value, p.amount.cents) for p in w.state.proposals) == [
        ("correction", 312000),
        ("credit_memo", 312000),
    ]
    assert len(w.state.receipts) == 2
    assert w.ledger_balance(w.facts.case_id).cents == 444000
    assert handle(w) == []


def test_silence_exactly_one_followup_and_restart_no_op():
    w = SchedulerWorld.wrap(hero())
    receipt = outbound(w)
    handle(w)
    assert w.state.due[0].basis == receipt.receipt_id
    assert w.state.due[0].due_at == receipt.at + timedelta(days=14)
    w.advance_to(15)
    assert handle(w) == [w.facts.case_id]
    assert len(w.state.proposals) == 1
    proposal = w.state.proposals[0]
    assert proposal.business_key.endswith(":follow_up:1")
    assert not ProposalValidator().validate(w, proposal, "approve")
    restarted = SchedulerWorld.wrap(w)
    restarted.events = deepcopy(w.events)
    assert handle(restarted) == []
    assert len(restarted.state.proposals) == 1
    assert len(w.state.receipts) == 1


def test_buyer_email_cancels_followup():
    w = SchedulerWorld.wrap(hero())
    outbound(w)
    handle(w)
    w.advance_to(5)
    add_email(w)
    handle(w)
    assert w.state.due[0].status == "cancelled"
    w.advance_to(15)
    handle(w)
    assert not any(p.kind == "follow_up" for p in w.state.proposals)


def test_unrelated_email_does_not_cancel():
    w = SchedulerWorld.wrap(hero())
    outbound(w)
    handle(w)
    w.advance_to(5)
    add_email(w, "SYNTHETIC stranger")
    handle(w)
    assert w.state.due[0].status == "pending"


def test_reply_after_basis_suppresses_overdue_work_even_without_email_event():
    w = SchedulerWorld.wrap(hero())
    outbound(w)
    handle(w)
    w.advance_to(15)
    add_email(w)
    w.events[-1].processed = True
    handle(w)
    assert not w.state.proposals
    assert w.state.due[0].status == "done"


def test_notice_deadline_minus_seven_and_claim_window():
    w = SchedulerWorld.wrap(insured_mixed())
    w.event("case_loaded")
    handle(w)
    notice = next(r for r in w.state.readiness if r.kind == "notice")
    due = next(d for d in w.state.due if d.kind == "notice_deadline")
    assert due.basis == notice.readiness_id
    assert due.due_at.date() == notice.deadline - timedelta(days=7)
    w.clock.start = due.due_at
    w.clock.current_day = 0
    handle(w)
    assert w.state.insurance == "notice_due"
    assert due.status == "done"
    p = next(p for p in w.state.proposals if p.kind == "insurer_notice")
    receipt = w.record(p, 1)
    receipt.at = w.clock.now()
    w.event("receipt_issued", receipt.receipt_id)
    handle(w)
    assert w.state.insurance == "claim_waiting"
    claim_due = next(d for d in w.state.due if d.kind == "claim_window")
    assert claim_due.due_at > receipt.at
    w.clock.start = claim_due.due_at
    w.clock.current_day = 0
    handle(w)
    assert any(p.kind == "claim_package" for p in w.state.proposals)
    assert claim_due.status == "done"


def test_event_exception_rolls_back_then_retries_once():
    w = SchedulerWorld.wrap(hero())
    w.state.decision = None
    w.event("case_loaded")
    w.fail_ack = True
    with pytest.raises(RuntimeError, match="crash after proposal"):
        handle(w)
    assert not w.state.proposals and w.state.decision is None
    assert not w.events[0].processed and not w.traces
    w.fail_ack = False
    handle(w)
    assert len(w.state.proposals) == 2 and w.events[0].processed
    assert handle(w) == []


def test_due_exception_rolls_back_proposal_and_ack():
    w = SchedulerWorld.wrap(hero())
    outbound(w)
    handle(w)
    w.advance_to(15)
    original = w.mark_due

    def crash(*args):
        original(*args)
        raise RuntimeError("SYNTHETIC due crash")

    w.mark_due = crash
    with pytest.raises(RuntimeError, match="due crash"):
        handle(w)
    assert not w.state.proposals and w.state.due[0].status == "pending"
    del w.mark_due
    handle(w)
    assert len(w.state.proposals) == 1


def test_duplicate_is_trace_only_and_events_sort_by_time_sequence():
    w = SchedulerWorld.wrap(hero())
    first = w.event("duplicate_ignored")
    second = w.event("duplicate_ignored")
    w.events.reverse()
    handle(w)
    assert [t.result["event_id"] for t in w.traces] == [first.event_id, second.event_id]
    assert not w.state.proposals


def test_followup_revalidation_rejects_early_forged_and_replied():
    w = SchedulerWorld.wrap(hero())
    outbound(w)
    handle(w)
    w.advance_to(15)
    handle(w)
    proposal = w.state.proposals[0]
    w.advance_to(1)
    assert "unsupported_proposal" in {
        i.code for i in ProposalValidator().validate(w, proposal, "save")
    }
    w.advance_to(15)
    add_email(w)
    for stage in ("save", "approve", "submit"):
        assert "unsupported_proposal" in {
            i.code for i in ProposalValidator().validate(w, proposal, stage)
        }


def test_new_receipt_replaces_followup_basis_and_uses_company_policy():
    w = SchedulerWorld.wrap(hero())
    pf, pe, _ = fact_inputs(
        [dict(id="company", kind="company_policy", fields={"follow_up_days": 3})], w.facts.case_id
    )
    w.facts.facts += pf.facts
    w.facts.docs += pf.docs
    w.inventory += pe
    first = outbound(w)
    handle(w)
    assert w.state.due[0].due_at == first.at + timedelta(days=3)
    w.advance_to(4)
    handle(w)
    second = w.record(w.state.proposals[0], 2)
    second.at = w.clock.now()
    w.event("receipt_issued", second.receipt_id)
    handle(w)
    pending = [d for d in w.state.due if d.status == "pending"]
    assert len(pending) == 1 and pending[0].basis == second.receipt_id
    w.advance_to(8)
    handle(w)
    assert [p.business_key.rsplit(":", 1)[-1] for p in w.state.proposals] == ["1", "2"]


def test_direct_investigation_schedules_notice_once():
    w = SchedulerWorld.wrap(insured_mixed())
    engine = HarnessEngine()
    engine.investigate(w, w.facts.case_id, FakeLLM(), "direct")
    engine.investigate(w, w.facts.case_id, FakeLLM(), "direct-again")
    assert len([d for d in w.state.due if d.kind == "notice_deadline"]) == 1


def test_policy_change_reschedules_claim_window():
    w = SchedulerWorld.wrap(insured_mixed())
    w.event("case_loaded")
    handle(w)
    receipt = w.record(next(p for p in w.state.proposals if p.kind == "insurer_notice"), 1)
    receipt.at = w.clock.now()
    w.event("receipt_issued", receipt.receipt_id)
    handle(w)
    old = next(d for d in w.state.due if d.kind == "claim_window")
    fact = next(f for f in w.facts.facts if f.key == "waiting_days_after_notice")
    fact.value += 10
    policy_doc = next(e for e in w.inventory if e.kind == "insurance_policy")
    policy_doc.fields["waiting_days_after_notice"] = fact.value
    w.event("evidence_superseded", policy_doc.evidence_id)
    handle(w)
    assert old.status == "cancelled"
    pending = [d for d in w.state.due if d.kind == "claim_window" and d.status == "pending"]
    assert len(pending) == 1
    assert pending[0].due_at == old.due_at + timedelta(days=10)
    assert pending[0].basis == receipt.receipt_id


def test_save_failure_rolls_back_event_before_ack(monkeypatch):
    w = SchedulerWorld.wrap(hero())
    w.event("case_loaded")
    original = w.save_proposal

    def crash(proposal):
        original(proposal)
        raise RuntimeError("SYNTHETIC crash immediately after save")

    with monkeypatch.context() as patch:
        patch.setattr(w, "save_proposal", crash)
        with pytest.raises(RuntimeError, match="immediately after save"):
            handle(w)
    assert not w.state.proposals and not w.events[0].processed
    handle(w)
    assert len(w.state.proposals) == 2
    assert handle(w) == []
