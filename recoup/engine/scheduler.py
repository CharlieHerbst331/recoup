"""Event and due-work handlers; design/02 §5.7."""

from datetime import datetime, time, timedelta
from hashlib import sha256
from uuid import uuid4

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import DueWork, Proposal, Target, TraceEvent
from recoup.engine import policy
from recoup.engine.derive import receipt_kind

OUTBOUND = {"dispute", "correction", "follow_up"}


def _buyer_email(world, case_id, evidence):
    recipients = world.allowed_recipients(case_id, Target.mock_buyer_portal)
    return evidence.kind == "email" and evidence.fields.get("from") in recipients


def _reply_after(world, case_id, receipt):
    return any(
        _buyer_email(world, case_id, e) and e.available_from > receipt.at
        for e in world.active_evidence(case_id)
    )


def _schedule(world, case_id, kind, at, basis):
    return world.schedule(
        DueWork(
            due_id=str(uuid4()),
            case_id=case_id,
            kind=kind,
            due_at=at,
            basis=basis,
            idempotency_key=(
                f"{case_id}:{kind}:{basis}:{at.isoformat()}"
                if kind == "claim_window"
                else f"{case_id}:{kind}:{basis}"
            ),
        )
    )


def _date_at(world, day):
    return datetime.combine(day, time.min, tzinfo=world.clock.now().tzinfo)


def schedule_notice(world, case_id):
    for r in world.readiness(case_id):
        if (
            r.kind == "notice"
            and r.status != "stale"
            and r.deadline
            and r.evidence_set_hash == world.evidence_set_hash(case_id)
        ):
            _schedule(
                world,
                case_id,
                "notice_deadline",
                _date_at(world, r.deadline - timedelta(days=7)),
                r.readiness_id,
            )


def followup_proposal(world, case_id, mode="fake"):
    """Return a code-owned due follow-up candidate; design/02 §5.7."""
    view = world.view(case_id)
    receipts = [r for r in view.receipts if receipt_kind(r, case_id) in OUTBOUND]
    receipt = max(receipts, key=lambda r: (r.at, r.receipt_id), default=None)
    if receipt is None or _reply_after(world, case_id, receipt):
        return None
    if not any(
        w.kind == "follow_up"
        and w.basis == receipt.receipt_id
        and w.status in {"pending", "done"}
        and w.due_at <= world.clock.now()
        for w in view.due
    ):
        return None
    decision = world.current_decision(case_id)
    if (
        not decision
        or not decision.current
        or decision.evidence_set_hash != world.evidence_set_hash(case_id)
    ):
        return None
    text = f"SYNTHETIC data. MOCK action. LLM {mode}. Please respond to the prior correspondence."
    sequence = 1 + sum(receipt_kind(r, case_id) == "follow_up" for r in view.receipts)
    return Proposal(
        proposal_id=str(uuid4()),
        case_id=case_id,
        business_key=f"{case_id}:follow_up:{sequence}",
        version=1,
        kind="follow_up",
        target=Target.mock_email,
        recipient=next(iter(world.allowed_recipients(case_id, Target.mock_email)), ""),
        amount=None,
        draft_text=text,
        draft_sha256=sha256(text.encode()).hexdigest(),
        citations=[],
        decision_id=decision.decision_id,
        decision_version=decision.version,
        evidence_set_hash=decision.evidence_set_hash,
        status="proposed",
        created_at=world.clock.now(),
        created_by="scheduler",
    )


def _receipt(world, event):
    case_id = event.case_id
    receipt = next(r for r in world.view(case_id).receipts if r.receipt_id == event.ref)
    kind = receipt_kind(receipt, case_id)
    if kind in OUTBOUND:
        world.cancel_due(case_id, "follow_up", "New outbound receipt")
        if _reply_after(world, case_id, receipt):
            return
        days = next(
            (
                f.value
                for f in world.fact_set(case_id).facts
                if f.doc_kind == "company_policy"
                and f.key == "follow_up_days"
                and type(f.value) is int
                and f.value > 0
                and f.trust not in {"ocr", "vision"}
            ),
            14,
        )
        _schedule(
            world, case_id, "follow_up", receipt.at + timedelta(days=days), receipt.receipt_id
        )
    elif kind == "insurer_notice":
        schedule_claim(world, case_id)
        world.set_status(case_id, insurance="claim_waiting")


def schedule_claim(world, case_id):
    view = world.view(case_id)
    receipt = max(
        (r for r in view.receipts if receipt_kind(r, case_id) == "insurer_notice"),
        key=lambda r: (r.at, r.receipt_id),
        default=None,
    )
    if receipt is None:
        return
    dates = [
        a.computed_date
        for a in policy.answer(world.fact_set(case_id), "claim_window", receipt)
        if a.computed_date
    ]
    at = _date_at(world, dates[0]) if dates else None
    if any(
        w.kind == "claim_window"
        and w.status == "pending"
        and (w.basis != receipt.receipt_id or w.due_at != at)
        for w in view.due
    ):
        world.cancel_due(case_id, "claim_window", "Notice or policy terms changed")
    if at:
        _schedule(world, case_id, "claim_window", at, receipt.receipt_id)


def handle(engine, world, llm, run_id):
    handled = []
    while True:
        events = [
            e for e in world.pending_events() if not e.processed and e.at <= world.clock.now()
        ]
        due = [w for w in world.due(world.clock.now()) if w.status == "pending"]
        # DueWork has no seq in the contract; events win ties, then stable due identity.
        work = [(e.at, 0, e.seq, e.event_id, e) for e in events]
        work += [(w.due_at, 1, 0, w.due_id, w) for w in due]
        if not work:
            return handled
        item = min(work, key=lambda row: row[:4])[-1]
        case_id = item.case_id
        with world.transaction():
            if isinstance(item, DueWork):
                if item.kind == "follow_up":
                    proposal = followup_proposal(world, case_id, getattr(llm, "mode", "fake"))
                    if proposal and not any(
                        p.business_key == proposal.business_key
                        and p.evidence_set_hash == proposal.evidence_set_hash
                        and p.status in {"proposed", "approved", "submitted_mock"}
                        for p in world.view(case_id).proposals
                    ):
                        from recoup.engine.gates import ProposalValidator

                        issues = ProposalValidator().validate(world, proposal, "save")
                        if issues:
                            raise GateError(issues)
                        world.save_proposal(proposal)
                else:
                    engine.investigate(world, case_id, llm, run_id)
                    schedule_notice(world, case_id)
                    schedule_claim(world, case_id)
                    if item.kind == "notice_deadline":
                        world.set_status(case_id, insurance="notice_due")
                world.mark_due(item.due_id, "done")
            else:
                if item.type == "receipt_issued":
                    _receipt(world, item)
                elif item.type != "duplicate_ignored":
                    if item.type in {"evidence_added", "evidence_superseded"}:
                        if _buyer_email(world, case_id, world.evidence(item.ref)):
                            world.cancel_due(case_id, "follow_up", "Buyer replied")
                    engine.investigate(world, case_id, llm, run_id)
                    schedule_notice(world, case_id)
                    schedule_claim(world, case_id)
                world.trace(
                    TraceEvent(
                        run_id=run_id,
                        case_id=case_id,
                        step=0,
                        sim_time=world.clock.now(),
                        kind="event",
                        controller="harness",
                        result_summary=item.type,
                        result={"event_id": item.event_id},
                    )
                )
                world.mark_event(item.event_id)
        if case_id not in handled:
            handled.append(case_id)
