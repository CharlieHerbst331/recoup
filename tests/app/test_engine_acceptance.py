"""Actual published-engine acceptance; provider absence is BLOCKED, never PASS."""

from importlib.util import find_spec

import pytest


@pytest.fixture
def engine_service():
    if find_spec("recoup.engine") is None:
        pytest.skip("BLOCKED G3: Sonny engine is published but not integrated into this checkout")
    from recoup.app import RecoupConfig, build

    service = build(RecoupConfig(db=":memory:"))
    assert service.runtime_provider == "engine"
    try:
        yield service
    finally:
        service.world.close()


def test_real_hero_has_current_approvable_proposals(engine_service):
    service = engine_service
    service.load(["cases/demo/H"])
    view = service.world.view("H")
    assert view.status != "needs_human", view.status_reason
    assert view.decision is not None
    proposals = [p for p in view.proposals if p.status in {"proposed", "approved"}]
    money = sorted(
        (p.kind.value, p.amount.cents) for p in proposals if p.kind in {"dispute", "credit_memo"}
    )
    assert money == [("credit_memo", 180000), ("dispute", 444000)]
    for proposal in proposals:
        assert (proposal.decision_id, proposal.decision_version) == (
            view.decision.decision_id,
            view.decision.version,
        )
    # Actual validator and approval must accept the generated versions unchanged.
    for proposal in proposals:
        if proposal.kind in {"dispute", "credit_memo"}:
            service.world.approve(proposal.proposal_id, proposal.version, "integration-reviewer")


def test_real_concede_demo_has_only_supported_credit(engine_service):
    service = engine_service
    service.load(["cases/demo/C"])
    view = service.world.view("C")
    assert view.status != "needs_human", view.status_reason
    assert view.decision is not None
    assert [(line.verdict.value, line.valid.cents) for line in view.decision.lines] == [
        ("valid", 50000)
    ]
    proposals = [p for p in view.proposals if p.status == "proposed"]
    assert [(p.kind.value, p.amount.cents) for p in proposals] == [("credit_memo", 50000)]
    service.world.approve(proposals[0].proposal_id, proposals[0].version, "integration-reviewer")


def test_real_unexplained_demo_requests_information_without_loop(engine_service):
    service = engine_service
    service.load(["cases/demo/N"])
    view = service.world.view("N")
    assert view.status != "needs_human", view.status_reason
    assert view.decision is not None
    assert [(line.line_id, line.verdict.value) for line in view.decision.lines] == [
        ("U1", "needs_info")
    ]
    proposals = [p for p in view.proposals if p.status == "proposed"]
    assert [p.kind.value for p in proposals] == ["info_request"]
    service.world.approve(proposals[0].proposal_id, proposals[0].version, "integration-reviewer")
