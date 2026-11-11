"""Distinct reviewer outcomes go through real facade operations, offline (§6)."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.interfaces import GateError
from recoup.ui.api import case_data, dashboard_data, mutate
from recoup.ui.reviewer import journey, update_summary

DEMO = Path(__file__).resolve().parents[2] / "recoup/ui/demo"


@pytest.fixture(scope="module")
def reviewer_database():
    service = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        service.load([str(DEMO / cid) for cid in ("H", "C", "N")])
        return service.world.db.serialize()
    finally:
        service.world.close()


@pytest.fixture
def reviewer(reviewer_database):
    service = build(RecoupConfig(db=":memory:", llm="fake"))
    service.world.db.deserialize(reviewer_database)
    try:
        yield service
    finally:
        service.world.close()


def test_three_distinct_outcomes_and_claim_document_gate(reviewer):
    service = reviewer
    seen, arrived = [], []
    blocked_version = None
    for _ in range(12):
        dashboard = dashboard_data(service)
        guide = dashboard["journey"]
        assert guide and not guide["out_of_order"]
        if guide["complete"]:
            break
        step = guide["current"]
        seen.append(step["id"])
        before = service.world.list_cases()
        if step["id"] == "statement-5":
            case = service.world.view("N")
            package = next(p for p in case.proposals if p.kind == "claim_package")
            assert package.status == "proposed"
            blocked_version = package.version
            claim = [r for r in case.readiness if r.kind == "claim" and r.status != "stale"][-1]
            assert claim.status == "not_ready"
            assert [(i.item_id, i.status) for i in claim.items if i.status != "present"] == [
                ("claim.doc.3", "missing")
            ]
            service.approve(package.proposal_id, package.version)
            with pytest.raises(GateError) as exc:
                service.submit(package.proposal_id, package.version)
            assert "claim_not_ready" in {issue.code for issue in exc.value.issues}
            assert not any(":claim_package:" in r.business_key for r in case.receipts)
        if step["action"] == "advance":
            mutate(service, "advance", {"to_next_due": True})
            arrived.append(service.world.clock.day())
        else:
            case = service.world.view(step["case_id"])
            proposal = next(p for p in case.proposals if p.proposal_id == step["proposal_id"])
            assert proposal.status == "proposed"
            if step["id"] == "claim-n":
                assert proposal.version > blocked_version
                assert any(
                    a.void and a.proposal_version == blocked_version
                    for a in service.history("N").approvals
                )
                claim = [r for r in case.readiness if r.kind == "claim" and r.status != "stale"][-1]
                assert claim.status == "ready"
                assert all(i.status == "present" for i in claim.items)
                titles = {e.evidence_id: e.doc_ref for e in case.evidence}
                assert {"INV", "POD", "STATEMENT", "COLLECTION"} <= {
                    titles[c.evidence_id] for c in proposal.citations
                }
                assert "$5,000.00" in proposal.draft_text
                assert "Agreed pricing credits are not unpaid trade debt" in proposal.draft_text
            payload = {"proposal_id": proposal.proposal_id, "version": proposal.version}
            with pytest.raises(GateError):
                mutate(service, "submit", payload)
            mutate(service, "approve", payload)
            mutate(service, "submit", payload)
        after = service.world.list_cases()
        assert update_summary(before, after)["changes"]
        assert all(c.status != "needs_human" for c in after)
    else:
        pytest.fail("Walkthrough did not finish")
    assert len(seen) == len(set(seen)) == 7
    assert arrived == [3, 5]
    assert guide["resolved"] == 2
    assert {c.case_id: c.open_balance.cents for c in after} == {"H": 0, "C": 0, "N": 500000}
    h, c, n = (service.world.view(cid) for cid in ("H", "C", "N"))
    assert c.decision.lines[0].verdict == "valid"
    assert h.decision.lines[0].verdict == "invalid"
    assert not any(r.target == "mock_erp" for r in h.receipts)
    assert [e.amount.cents for e in service.history("H").ledger if e.source == "REPAYMENT"] == [
        312000
    ]
    assert next(line for line in n.decision.lines if line.line_id == "D1").valid.cents == 215000
    assert not any(
        e.kind == "payment" and e.at.date() > service.history("N").ledger[0].at.date()
        for e in service.history("N").ledger
    )
    dashboard = dashboard_data(service)
    assert dashboard["new_payments"] == "$3,120.00"
    assert dashboard["claims_submitted_count"] == 1
    assert case_data(service, "H")["new_payments"] == "$3,120.00"
    assert case_data(service, "C")["new_payments"] == "$0.00"
    detail = case_data(service, "N")
    assert detail["brief"]["label"] == "MOCK claim submitted"
    assert len(detail["receipt_records"]) == 3  # credit, notice, claim; no payment
    assert all(r["approvals"] for r in detail["receipt_records"])


def test_future_statement_and_buyer_repayment_are_hidden_until_release(reviewer):
    for cid in ("H", "N"):
        detail = case_data(reviewer, cid)
        assert not any(
            d["evidence"]["doc_ref"] in {"REPAYMENT", "BUYER-ACK", "STATEMENT"}
            for d in detail["documents"]
        )
        for trace in reviewer.history(cid).traces:
            if trace.kind == "model_call":
                assert "EV-N-STATEMENT" not in str(trace.request)
                assert "NW-1042-REP" not in str(trace.request)
    assert case_data(reviewer, "N")["decision_changes"] == []


def test_early_manual_advance_discloses_missed_correspondence(reviewer):
    reviewer.advance(days=3)
    guide = journey(reviewer.world.list_cases())
    assert guide["out_of_order"]
    assert not guide["complete"]


def test_policy_cross_checks_and_exclusion_are_recorded_not_ui_inventions(reviewer):
    detail = case_data(reviewer, "N")
    assert {a["question"] for a in detail["policy_review"]} == {
        "applicability",
        "notice deadline",
        "claim window",
        "claim documents",
        "disputed debt",
        "credit limit",
        "exclusions",
    }
    assert any(
        a["question"] == "credit limit" and a["result"] == "$10,000.00"
        for a in detail["policy_review"]
    )
    exclusion = next(a for a in detail["policy_review"] if a["question"] == "exclusions")
    assert "Agreed pricing credits" in exclusion["result"]
    assert exclusion["citations"]
    assert (
        next(a for a in detail["policy_review"] if a["clause_key"] == "claim_doc.3")["result"]
        == "statement"
    )
    assert any(
        p["current"]["kind"] == "insurer_notice"
        and "Recorded policy checks" in p["current"]["draft_text"]
        for p in detail["proposals"]
    )
