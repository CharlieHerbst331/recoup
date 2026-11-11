"""Saved offline drafts use actual rules, policy answers, and source citations."""

from pathlib import Path

from recoup.app import RecoupConfig, build
from recoup.engine.gates import assertion_issues


def test_saved_offline_drafts_are_specific_cited_and_pass_existing_assertion_gate():
    service = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        root = Path(__file__).resolve().parents[2] / "recoup/ui/demo"
        service.load([str(root / cid) for cid in ("H", "C", "N")])
        for case in service.world.list_cases():
            assert case.status != "needs_human"
            for proposal in case.proposals:
                assert "Subject:" in proposal.draft_text
                assert case.buyer in proposal.draft_text
                assert "LLM fake" in proposal.draft_text and "MOCK" in proposal.draft_text
                assert proposal.citations
                assert not assertion_issues(proposal.draft_text, proposal.citations)
        case = service.world.view("N")
        assert (
            next(line for line in case.decision.lines if line.line_id == "D1").valid.cents == 215000
        )
        nonpayment = next(line for line in case.decision.lines if line.line_id == "NP")
        assert "not a valid buyer deduction" in nonpayment.rationale
        questions = {
            t.args["question"] for t in service.history("N").traces if t.tool == "check_policy"
        }
        assert {"exclusions", "applicability", "claim_documents", "credit_limit"} <= questions
    finally:
        service.world.close()
