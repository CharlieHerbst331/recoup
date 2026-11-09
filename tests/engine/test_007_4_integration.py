"""Real-provider acceptance for 007-4; absent G1/G2/G3 is explicitly BLOCKED."""

from importlib.util import find_spec

import pytest

from recoup.contracts.testing import NullController
from recoup.engine.harness import HarnessEngine
from recoup.engine.llm import FakeLLM

from .test_007_3_integration import bundle
from .test_harness_factory_ingest import doc, scripted, write_pdf


def test_real_reinvestigation_preserves_approved_proposals(world):
    cid = load(world)
    engine = HarnessEngine()
    first = engine.investigate(world, cid, FakeLLM(), "first")
    assert first.proposals
    approvals = [
        world.approve(p.proposal_id, p.version, "SYNTHETIC reviewer") for p in first.proposals
    ]
    second = engine.investigate(world, cid, FakeLLM(), "second")
    assert second.status != "needs_human", second.status_reason
    assert second.decision == first.decision
    assert all(p.status == "approved" for p in second.proposals)
    assert [(p.proposal_id, p.version) for p in second.proposals] == [
        (p.proposal_id, p.version) for p in first.proposals
    ]
    assert world.history(cid).approvals == approvals
    for proposal in second.proposals:
        world.submit(proposal.proposal_id, proposal.version)


@pytest.fixture
def world():
    if find_spec("recoup.app") is None:
        pytest.skip("BLOCKED G1/G2/G3: app.build, SqliteWorld and actual factory wiring absent")
    from recoup.app import RecoupConfig, build

    return build(RecoupConfig(db=":memory:"), controller=NullController()).world


def load(world, mixed=False):
    b = bundle()
    if mixed:
        from recoup.contracts.bundle import BundleDoc

        b.docs = [d for d in b.docs if d.kind != "pod"]
        invoice = next(d for d in b.docs if d.kind == "invoice")
        invoice.fields.update(buyer_id="BUYER", invoice_date="2026-08-03", due_date="2026-09-02")
        b.docs.append(
            BundleDoc(
                doc_ref="policy",
                kind="insurance_policy",
                title="SYNTHETIC",
                fields={
                    "covered_buyer.1": "BUYER",
                    "period_start": "2026-01-01",
                    "period_end": "2026-12-31",
                    "mep_days_after_due": 0,
                    "notice_days_after_mep": 90,
                    "waiting_days_after_notice": 60,
                    "disputed_debt_clause": "notice_still_required",
                    "clause.notice_still_required": "SYNTHETIC notice still required.",
                },
            )
        )
    assert world.load_bundle(b).status == "loaded"
    return b.case_id


def test_real_hero_harness(world):
    cid = load(world)
    result = HarnessEngine().investigate(world, cid, FakeLLM(), "real-hero")
    assert result.status != "needs_human", result.status_reason
    assert sorted((p.kind.value, p.amount.cents) for p in result.proposals) == [
        ("credit_memo", 180000),
        ("dispute", 444000),
    ]
    assert not result.receipts


def test_real_mixed_insurance_isolation(world):
    cid = load(world, mixed=True)
    result = HarnessEngine().investigate(world, cid, FakeLLM(), "real-mixed")
    assert result.status != "needs_human", result.status_reason
    assert next(d for d in result.decision.lines if d.line_id == "D1").verdict == "needs_info"
    assert any(
        p.kind == "dispute" and [a.line_id for a in p.allocations] == ["D2"]
        for p in result.proposals
    )
    assert any(r.kind == "notice" and r.status == "ready" for r in result.readiness)


@pytest.mark.parametrize(
    "calls,reason",
    [
        ([("end", {"reason": "premature"})], "current decision"),
        ([("run_rules", {}), ("run_rules", {})], "loop"),
    ],
)
def test_real_completion_and_loop(world, calls, reason):
    cid = load(world)
    result = HarnessEngine().investigate(world, cid, scripted(*calls), "real-guard")
    assert result.status == "needs_human" and reason in result.status_reason


def test_real_model_verdict_override(world):
    cid = load(world)
    llm = scripted(
        (
            "propose_decision",
            {"lines": [dict(line_id="D1", verdict="valid", citations=[], rationale="SYNTHETIC")]},
        )
    )
    HarnessEngine().investigate(world, cid, llm, "real-override")
    decision = world.current_decision(cid)
    assert decision.lines[0].verdict == "invalid"
    assert decision.lines[0].disputed.cents == 312000


def test_real_pdf_loader_factory_ingestor(world, tmp_path):
    cid = load(world)
    write_pdf(tmp_path / "generated.pdf")
    evidence = world.add_evidence(cid, doc(file="generated.pdf"), str(tmp_path))
    assert evidence.readable and evidence.method == "text_pdf"
    assert evidence.text == "SYNTHETIC POD signed\freceived 360"
