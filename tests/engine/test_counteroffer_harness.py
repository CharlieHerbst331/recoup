"""Counteroffer harness and selected-case execution; design/02 §4.5, §5.4–5.6."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import CaseBundle
from recoup.contracts.testing import NullController
from recoup.engine.harness import HarnessEngine, _draft_args
from recoup.engine.llm import FakeLLM
from recoup.engine.tools import ToolSessionFactory


@pytest.fixture
def bundle():
    return CaseBundle.model_validate_json(
        (
            Path(__file__).resolve().parents[2] / "cases/ambition/counteroffer/bundle.json"
        ).read_text()
    )


@pytest.fixture
def service():
    app = build(RecoupConfig(db=":memory:"), controller=NullController())
    try:
        yield app
    finally:
        app.world.close()


def test_fake_selects_opaque_counteroffer_without_money_and_requests_approval(service, bundle):
    world = service.world
    world.load_bundle(bundle)
    result = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "fake-offer-tools")
    assert result.status != "needs_human", result.status_reason
    traces = world.history(bundle.case_id).traces
    calls = [c for t in traces if t.kind == "model_call" for c in t.result["tool_calls"]]
    offer = next(
        c
        for c in calls
        if c["name"] == "draft_proposal" and c["arguments"]["kind"] == "counteroffer"
    )
    args = offer["arguments"]
    assert args["offer_ref"] == "A/B"
    assert args["line_ids"] == ["D2"]
    assert "amount" not in args and "allocations" not in args and "amount_cents" not in args
    assert "Conditional" in args["draft_text"] and "MOCK" in args["draft_text"]
    proposal = next(p for p in result.proposals if p.kind == "counteroffer")
    assert proposal.offer_ref == "A/B" and proposal.amount.cents == 10000
    assert any(
        c["name"] == "request_approval"
        and c["arguments"] == {"proposal_id": proposal.proposal_id, "version": proposal.version}
        for c in calls
    )
    assert calls[-1]["name"] == "end"
    assert traces[-1].result["result"]["accepted"]
    assert proposal.status == "proposed" and not result.receipts
    assert all(t.llm_mode == "fake" for t in traces if t.kind in {"model_call", "tool_call"})


def test_completion_requires_counteroffer_and_accepts_existing_draft_and_receipt(service, bundle):
    from recoup.engine.derive import derive

    world = service.world
    world.load_bundle(bundle)
    session = ToolSessionFactory().open(world, bundle.case_id, "offer-completion", "test")
    findings = session.call("run_rules", {}).result["findings"]
    decision = session.call(
        "propose_decision",
        {
            "lines": [
                dict(
                    line_id=f["line_id"],
                    verdict=f["verdict"],
                    citations=f["citations"],
                    rationale="SYNTHETIC",
                )
                for f in findings
            ]
        },
    )
    assert decision.ok and decision.result["accepted"]
    candidates = derive(world, bundle.case_id)
    offer = next(p for p in candidates if p.kind == "counteroffer")
    for proposal in candidates:
        if proposal.kind != "counteroffer":
            saved = session.call("draft_proposal", _draft_args(world, proposal, "fake"))
            assert saved.ok and saved.result["accepted"]
    end = session.call("end", {"reason": "ordinary proposals only"})
    assert end.ok and not end.result["accepted"]
    assert end.result["unmet"] == [offer.business_key]
    drafted = session.call("draft_proposal", _draft_args(world, offer, "fake"))
    assert drafted.ok and drafted.result["accepted"]
    assert session.call("end", {"reason": "offer drafted"}).result["accepted"]
    pid, version = drafted.result["proposal_id"], drafted.result["version"]
    world.approve(pid, version, "SYNTHETIC reviewer")
    before = world.ledger(bundle.case_id)
    receipt = world.submit(pid, version)
    assert receipt.offer_ref == "A/B" and receipt.receipt_id.startswith("MOCK-")
    assert world.ledger(bundle.case_id) == before
    assert session.call("end", {"reason": "offer submitted"}).result["accepted"]
    assert not any(p.kind == "counteroffer" for p in derive(world, bundle.case_id))


def test_selected_case_fake_run_leaves_other_case_events_and_state_untouched(bundle):
    app = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        other = bundle.model_copy(deep=True, update={"case_id": "OTHER-COUNTEROFFER"})
        # Seed through the real World to retain pending work for both cases.
        app.world.load_bundle(bundle)
        app.world.load_bundle(other)
        from recoup.contracts.models import DueWork

        app.world.schedule(
            DueWork(
                due_id="OTHER-DUE",
                case_id=other.case_id,
                kind="recheck",
                due_at=app.world.clock.now(),
                basis=app.world.evidence_set_hash(other.case_id),
                idempotency_key="OTHER-DUE",
            )
        )
        before = app.world.history(other.case_id).model_dump(mode="json")
        pending = [
            e.model_dump(mode="json")
            for e in app.world.pending_events()
            if e.case_id == other.case_id
        ]
        result = app.run(bundle.case_id)
        assert [v.case_id for v in result] == [bundle.case_id]
        assert any(p.kind == "counteroffer" for p in result[0].proposals)
        assert not result[0].receipts
        assert app.world.history(other.case_id).model_dump(mode="json") == before
        assert [
            e.model_dump(mode="json")
            for e in app.world.pending_events()
            if e.case_id == other.case_id
        ] == pending
        assert app.world.current_decision(other.case_id) is None
        assert (
            next(d for d in app.world.view(other.case_id).due if d.due_id == "OTHER-DUE").status
            == "pending"
        )
        assert all(t.case_id == bundle.case_id for t in app.world.history(bundle.case_id).traces)
    finally:
        app.world.close()


@pytest.mark.parametrize("blocked", ["expired", "authority"])
def test_fake_completes_ordinary_work_when_no_counteroffer_is_available(service, bundle, blocked):
    if blocked == "expired":
        offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
        offer.fields["offer.A/B.expires_date"] = "2020-01-01"
    else:
        policy = next(d for d in bundle.docs if d.kind == "company_policy")
        policy.fields["authority_cents"] = 9999
    world = service.world
    world.load_bundle(bundle)
    result = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "blocked-offer")
    assert result.status != "needs_human", result.status_reason
    assert not any(p.kind == "counteroffer" for p in result.proposals)
    assert any(p.kind == "credit_memo" for p in result.proposals)
    end = [t for t in world.history(bundle.case_id).traces if t.tool == "end"][-1]
    assert end.result["result"] == {"accepted": True, "unmet": []}
