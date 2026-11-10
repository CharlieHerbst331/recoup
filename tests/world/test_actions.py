"""SQLite orchestration and financial guards; explicit PassValidator is not G3 proof."""

from datetime import timedelta

import pytest

from recoup.contracts.bundle import BundleDoc, BundleEvent
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.models import (
    CaseStatus,
    Citation,
    Decision,
    DueWork,
    FieldTrust,
    GateIssue,
    LineAmount,
    LineDecision,
    Money,
    Proposal,
    ProposalStatus,
    Readiness,
)
from recoup.contracts.testing import stub_parts
from recoup.world import SqliteWorld


def decide(world, valid=2000, disputed=0):
    return world.save_decision(
        Decision(
            decision_id="D",
            case_id="CASE",
            version=1,
            evidence_set_hash=world.evidence_set_hash("CASE"),
            current=True,
            lines=[
                LineDecision(
                    line_id="U1",
                    verdict="valid" if disputed == 0 else "partial",
                    basis="proven",
                    valid=Money(cents=valid),
                    disputed=Money(cents=disputed),
                    citations=[],
                    rationale="Explicit test decision",
                )
            ],
            model_id="test",
            llm_mode="fake",
            prompt_version="test",
            created_at=world.clock.now(),
        )
    )


def offer(
    world,
    kind="credit_memo",
    cents=1000,
    key=None,
    identity=None,
    corrects=None,
    allocations=None,
    decision=True,
):
    current = world.current_decision("CASE")
    if allocations is None:
        allocations = [LineAmount(line_id="U1", amount=Money(cents=cents))]
    targets = {
        "credit_memo": "mock_erp",
        "correction": "mock_buyer_portal",
        "dispute": "mock_buyer_portal",
        "insurer_notice": "mock_insurer",
        "claim_package": "mock_insurer",
        "info_request": "mock_email",
    }
    target = targets[kind]
    return world.save_proposal(
        Proposal(
            proposal_id=identity or f"P-{kind}-{key or 'base'}",
            business_key=key or f"CASE:{kind}:U1",
            version=1,
            case_id="CASE",
            kind=kind,
            target=target,
            recipient="ERP" if target == "mock_erp" else "buyer@example.test",
            allocations=allocations,
            amount=Money(cents=cents),
            draft_text="SYNTHETIC MOCK test draft.",
            draft_sha256="",
            citations=[],
            decision_id=current.decision_id if current and decision else None,
            decision_version=current.version if current and decision else None,
            evidence_set_hash=world.evidence_set_hash("CASE"),
            corrects_receipt_id=corrects,
            balance_basis=world.ledger_balance("CASE")
            if kind in {"insurer_notice", "claim_package"}
            else None,
            status="proposed",
            created_at=world.clock.now(),
            created_by="agent",
        )
    )


def approve(world, proposal):
    world.approve(proposal.proposal_id, proposal.version, "Charles")
    return proposal


def submit(world, proposal):
    return world.submit(proposal.proposal_id, proposal.version)


def raw(world, table):
    return [tuple(row) for row in world.db.execute(f"SELECT * FROM {table} ORDER BY rowid")]


def test_no_approval_and_unknown_calls_have_exactly_one_attempt(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    p = offer(world)
    for identity, version, code in [
        (p.proposal_id, p.version, "not_approved"),
        (p.proposal_id, 99, "unknown_proposal"),
        ("unknown", 1, "unknown_proposal"),
    ]:
        before = len(raw(world, "attempts"))
        with pytest.raises(GateError, match=code):
            world.submit(identity, version)
        assert len(raw(world, "attempts")) == before + 1
    assert [a.outcome for a in world.history("CASE").attempts] == ["gate_rejected", "gate_rejected"]
    assert (
        world.db.execute("SELECT case_id FROM attempts ORDER BY rowid DESC").fetchone()[0]
        == "__unknown__"
    )
    assert not world.history("CASE").receipts


def test_credit_posts_once_and_replay_precedes_stale_validator_and_failure(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    p = approve(world, offer(world))
    receipt = submit(world, p)
    assert receipt.receipt_id == "MOCK-CM-0001"
    assert world.ledger_balance("CASE").cents == 1000
    before = raw(world, "ledger"), raw(world, "receipts")
    world.add_evidence("CASE", BundleDoc(doc_ref="NEW", kind="email", title="New", text="Reply"))
    world.fail_next("mock_erp")

    class RejectAll:
        def validate(self, world, proposal, stage):
            raise AssertionError("Replay must precede validation")

    world.validator = RejectAll()
    assert submit(world, p) == receipt
    assert (raw(world, "ledger"), raw(world, "receipts")) == before
    assert [a.outcome for a in world.history("CASE").attempts] == ["receipt", "idempotent_return"]
    assert world.db.execute("SELECT 1 FROM meta WHERE key='fail_next:mock_erp'").fetchone()
    assert not world.current_decision("CASE")


def test_stale_fact_voids_approval_and_identical_fact_does_nothing(world, bundle):
    world.load_bundle(bundle)
    row = next(e for e in world.active_evidence("CASE") if e.doc_ref == "POD")
    citation = Citation(evidence_id=row.evidence_id, locator="text", quote="Received 80 cases.")
    fact = world.add_fact(
        row.evidence_id, "received.SKU-1", 80, FieldTrust.model_extracted, citation, "model"
    )
    decide(world)
    p = approve(world, offer(world))
    before = (
        raw(world, "proposals"),
        raw(world, "approvals"),
        raw(world, "traces"),
        raw(world, "events"),
    )
    assert world.add_fact(row.evidence_id, fact.key, 80, fact.trust, citation, "model") == fact
    assert (
        raw(world, "proposals"),
        raw(world, "approvals"),
        raw(world, "traces"),
        raw(world, "events"),
    ) == before
    world.confirm_field(row.evidence_id, fact.key, "Charles")
    assert world.history("CASE").approvals[0].void
    assert world.view("CASE").proposals[0].status == "stale"
    with pytest.raises(GateError, match="not_approved"):
        submit(world, p)


def test_approval_binding_tamper_and_validator_submit_stage(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    p = approve(world, offer(world))
    altered = world._proposal(p.proposal_id, p.version).model_copy(
        update={"recipient": "different"}
    )
    world._write_proposal(altered)
    with pytest.raises(GateError, match="approval_mismatch"):
        submit(world, p)
    world._write_proposal(p.model_copy(update={"status": ProposalStatus.approved}))

    class RejectSubmit:
        def validate(self, world, proposal, stage):
            return (
                [GateIssue(code="finance_gate", message="explicit test gate")]
                if stage == "submit"
                else []
            )

    world.validator = RejectSubmit()
    with pytest.raises(GateError, match="finance_gate"):
        submit(world, p)
    assert not world.history("CASE").receipts
    assert len(world.history("CASE").attempts) == 2


def test_new_decision_invalidates_old_decision_binding_at_submit(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    p = approve(world, offer(world))
    decide(world)
    with pytest.raises(GateError, match="stale_decision"):
        submit(world, p)


def test_aggregate_duplicate_credit_allocations_cannot_bypass_valid_guard(world, bundle):
    world.load_bundle(bundle)
    decide(world, valid=1500, disputed=500)
    p = approve(
        world,
        offer(
            world,
            cents=1600,
            allocations=[
                LineAmount(line_id="U1", amount=Money(cents=800)),
                LineAmount(line_id="U1", amount=Money(cents=800)),
            ],
        ),
    )
    with pytest.raises(GateError, match="credit_exceeds_valid"):
        submit(world, p)
    assert world.ledger_balance("CASE").cents == 2000
    assert not world.history("CASE").receipts


def test_remaining_credit_and_business_key_guards(world, bundle):
    world.load_bundle(bundle)
    decide(world, valid=1500, disputed=500)
    first = approve(world, offer(world, cents=1000))
    second = approve(world, offer(world, cents=600, key="CASE:credit_memo:U1:inc:1"))
    submit(world, first)
    with pytest.raises(GateError, match="credit_exceeds_valid"):
        submit(world, second)
    with pytest.raises(GateError, match="already_submitted"):
        offer(world, cents=1000, identity="OTHER")
    # A new id cannot evade submit's business uniqueness either.
    forged = first.model_copy(
        update={
            "proposal_id": "FORGED",
            "status": ProposalStatus.approved,
            "draft_text": "Changed",
            "draft_sha256": "changed",
        }
    )
    world._write_proposal(forged)
    with pytest.raises(GateError, match="already_submitted"):
        submit(world, forged)
    assert world.ledger_balance("CASE").cents == 1000


def test_preexisting_credit_and_open_balance_guards(world, bundle):
    bundle.docs.append(
        BundleDoc(
            doc_ref="OLD-CM",
            kind="credit_memo",
            title="Prior",
            fields={"amount_cents": 500, "line_id": "U1"},
        )
    )
    world.load_bundle(bundle)
    decide(world, valid=1000, disputed=500)
    p = approve(world, offer(world, cents=600))
    with pytest.raises(GateError, match="credit_exceeds_valid"):
        submit(world, p)
    decide(world, valid=10000)
    p2 = approve(world, offer(world, cents=1600, key="CASE:credit_memo:U1:inc:1"))
    with pytest.raises(GateError, match="credit_exceeds_balance"):
        submit(world, p2)


def test_notice_and_claim_stale_on_balance_and_due_cancelled(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    credit = approve(world, offer(world))
    notices = []
    for kind in ("insurer_notice", "claim_package"):
        readiness = world.save_readiness(
            Readiness(
                readiness_id=f"R-{kind}",
                case_id="CASE",
                kind="notice" if kind == "insurer_notice" else "claim",
                status="ready",
                items=[],
                evidence_set_hash=world.evidence_set_hash("CASE"),
                balance_basis=world.ledger_balance("CASE"),
            )
        )
        p = approve(world, offer(world, kind=kind))
        notices.append(p)
        world.schedule(
            DueWork(
                due_id=kind,
                case_id="CASE",
                kind="recheck",
                due_at=world.clock.now(),
                basis=p.proposal_id,
                idempotency_key=kind,
            )
        )
        world.schedule(
            DueWork(
                due_id=readiness.readiness_id,
                case_id="CASE",
                kind="recheck",
                due_at=world.clock.now(),
                basis=readiness.readiness_id,
                idempotency_key=readiness.readiness_id,
            )
        )
    submit(world, credit)
    assert all(
        p.status == "stale"
        for p in world.view("CASE").proposals
        if p.kind in {"insurer_notice", "claim_package"}
    )
    assert all(r.status == "stale" for r in world.readiness("CASE"))
    assert not world.due(world.clock.now())
    assert all(
        a.void
        for a in world.history("CASE").approvals
        if a.proposal_id in {p.proposal_id for p in notices}
    )


def test_cascade_reopens_closed_and_keeps_receipts_and_ledger_bytes(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    submit(world, approve(world, offer(world)))
    before = raw(world, "receipts"), raw(world, "ledger")
    world.set_status(
        "CASE",
        status=CaseStatus.closed,
    )
    trace_count = len(world.history("CASE").traces)
    world.add_evidence(
        "CASE", BundleDoc(doc_ref="REPLY", kind="email", title="Reply", text="New facts")
    )
    assert world.view("CASE").status == "investigating"
    assert world.history("CASE").events[-1].type == "reopened"
    assert len(world.history("CASE").traces) == trace_count + 1
    assert world.history("CASE").traces[-1].result_summary == "reopened"
    assert (raw(world, "receipts"), raw(world, "ledger")) == before


def test_corrections_use_per_receipt_per_line_pools(world, bundle):
    world.load_bundle(bundle)
    decide(world, valid=0, disputed=2000)
    first = submit(world, approve(world, offer(world, kind="dispute", cents=1000)))
    supplement = submit(
        world, approve(world, offer(world, kind="dispute", cents=200, key="CASE:dispute:U1:inc:1"))
    )
    correction1 = offer(
        world,
        kind="correction",
        cents=200,
        corrects=supplement.receipt_id,
        key=f"CASE:correction:{supplement.receipt_id}:1",
    )
    submit(world, approve(world, correction1))
    invalid = offer(
        world,
        kind="correction",
        cents=1,
        corrects=supplement.receipt_id,
        key=f"CASE:correction:{supplement.receipt_id}:2",
    )
    with pytest.raises(GateError, match="correction_exceeds_receipt"):
        submit(world, approve(world, invalid))
    correction2 = offer(
        world,
        kind="correction",
        cents=700,
        corrects=first.receipt_id,
        key=f"CASE:correction:{first.receipt_id}:1",
    )
    submit(world, approve(world, correction2))
    receipts = world.history("CASE").receipts
    assert sum(r.amount.cents * (-1 if r.corrects_receipt_id else 1) for r in receipts) == 300
    # Duplicate allocations must not each compare against the same remaining 300.
    invalid2 = offer(
        world,
        kind="correction",
        cents=400,
        corrects=first.receipt_id,
        key=f"CASE:correction:{first.receipt_id}:2",
        allocations=[
            LineAmount(line_id="U1", amount=Money(cents=200)),
            LineAmount(line_id="U1", amount=Money(cents=200)),
        ],
    )
    with pytest.raises(GateError, match="correction_exceeds_receipt"):
        submit(world, approve(world, invalid2))


def test_correction_cannot_withdraw_credit_or_other_case_receipt(world, bundle):
    world.load_bundle(bundle)
    decide(world)
    credit = submit(world, approve(world, offer(world)))
    invalid = offer(world, kind="correction", cents=1, corrects=credit.receipt_id)
    with pytest.raises(GateError, match="invalid_correction_receipt"):
        submit(world, approve(world, invalid))
    other = bundle.model_copy(update={"case_id": "OTHER"})
    world.load_bundle(other)
    p = invalid.model_copy(
        update={
            "proposal_id": "OTHER-P",
            "case_id": "OTHER",
            "business_key": "OTHER:correction:bad:1",
            "evidence_set_hash": world.evidence_set_hash("OTHER"),
            "decision_id": None,
            "decision_version": None,
            "status": "proposed",
        }
    )
    p = world.save_proposal(p)
    with pytest.raises(GateError, match="invalid_correction_receipt"):
        submit(world, approve(world, p))


def test_transient_rollback_retry_and_restart(tmp_path, bundle):
    parts = stub_parts()
    path = str(tmp_path / "world.db")
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    world.load_bundle(bundle)
    decide(world)
    p = approve(world, offer(world))
    before = (
        raw(world, "ledger"),
        raw(world, "receipts"),
        raw(world, "events"),
        raw(world, "proposals"),
    )
    world.fail_next("mock_erp")
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    with pytest.raises(TransientError):
        submit(world, p)
    assert (
        raw(world, "ledger"),
        raw(world, "receipts"),
        raw(world, "events"),
        raw(world, "proposals"),
    ) == before
    assert world.history("CASE").attempts[-1].outcome == "transient_error"
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    receipt = submit(world, p)
    assert receipt.receipt_id == "MOCK-CM-0001"
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    assert submit(world, p) == receipt
    assert [a.outcome for a in world.history("CASE").attempts] == [
        "transient_error",
        "receipt",
        "idempotent_return",
    ]
    world.close()


def test_exception_after_receipt_rolls_back_all_effects_and_is_audited(world, bundle, monkeypatch):
    world.load_bundle(bundle)
    decide(world)
    p = approve(world, offer(world))
    before = {
        table: raw(world, table)
        for table in ("ledger", "receipts", "events", "proposals", "traces")
    }
    original = world._cascade

    def fail(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("simulate storage failure after financial writes")

    monkeypatch.setattr(world, "_cascade", fail)
    with pytest.raises(RuntimeError, match="simulate storage"):
        submit(world, p)
    assert {table: raw(world, table) for table in before} == before
    assert world.history("CASE").attempts[-1].outcome == "transient_error"
    monkeypatch.setattr(world, "_cascade", original)
    assert submit(world, p).receipt_id == "MOCK-CM-0001"


def test_classified_unexplained_claim_stays_gross_after_posted_credit(world, bundle):
    world.load_bundle(bundle)
    world.set_line_reason("CASE", "U1", "shortage", FieldTrust.human_confirmed, None)
    decide(world, valid=2000)
    submit(world, approve(world, offer(world, cents=1000)))
    assert world.deduction_lines("CASE")[0].claimed.cents == 2000
    assert world.deduction_lines("CASE")[0].reason == "shortage"
    second = approve(world, offer(world, cents=1000, key="CASE:credit_memo:U1:inc:1"))
    submit(world, second)
    assert world.ledger_balance("CASE").cents == 0
    assert world.deduction_lines("CASE")[0].claimed.cents == 2000


def test_events_due_and_held_visibility_survive_restart_exactly_once(tmp_path, bundle):
    bundle.docs.append(
        BundleDoc(
            doc_ref="HELD",
            kind="pod",
            title="Shipping POD",
            text="Hidden manifest",
            held_by="shipping",
            available_at_day=2,
        )
    )
    bundle.events = [
        BundleEvent(
            at_day=3,
            type="add_doc",
            doc=BundleDoc(doc_ref="REPLY", kind="email", title="Reply", text="Hello"),
        )
    ]
    parts = stub_parts()
    path = str(tmp_path / "events.db")
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    world.load_bundle(bundle)
    for event in world.pending_events():
        world.mark_event(event.event_id)
    world.schedule(
        DueWork(
            due_id="DUE",
            case_id="CASE",
            kind="recheck",
            due_at=world.clock.now() + timedelta(days=3),
            basis="test",
            idempotency_key="due",
        )
    )
    assert world.next_due_day() == 2
    assert world.attach_held("CASE", "shipping", "manifest") == []
    world.advance_to(2)
    assert world.next_due_day() == 3
    assert not any(e.doc_ref == "HELD" for e in world.active_evidence("CASE"))
    world.fail_next("shipping")
    with pytest.raises(TransientError):
        world.attach_held("CASE", "shipping", "manifest")
    assert len(world.attach_held("CASE", "shipping", "manifest")) == 1
    assert world.attach_held("CASE", "shipping", "manifest") == []
    events = world.advance_to(3)
    assert any(event.ref == "EV-CASE-REPLY-v1" for event in events)
    assert world.advance_to(3) == []
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    pending = world.pending_events()
    assert len({event.event_id for event in pending}) == len(pending)
    assert [work.due_id for work in world.due(world.clock.now())] == ["DUE"]
    for event in pending:
        world.mark_event(event.event_id)
    world.mark_due("DUE", "done")
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    assert world.pending_events() == []
    assert world.due(world.clock.now()) == []
    assert world.next_due_day() is None
    world.close()


def test_future_direct_evidence_is_hidden_during_calendar_only_advance(world, bundle):
    world.load_bundle(bundle)
    initial = world.evidence_set_hash("CASE")
    assert (
        world.add_evidence(
            "CASE",
            BundleDoc(
                doc_ref="FUTURE",
                kind="payment",
                title="Future",
                available_at_day=5,
                fields={"paid_cents": 500},
            ),
        )
        is None
    )
    world.advance_to(5, release_events=False)
    assert world.evidence_set_hash("CASE") == initial
    assert world.ledger_balance("CASE").cents == 2000
    assert not any(e.doc_ref == "FUTURE" for e in world.active_evidence("CASE"))
    events = world.advance_to(5)
    assert world.ledger_balance("CASE").cents == 1500
    assert [event.type for event in events] == ["evidence_added", "ledger_changed"]
