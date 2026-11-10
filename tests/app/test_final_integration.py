"""Published SYNTHETIC demo through the actual fake-engine application facade."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.interfaces import GateError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def service():
    app = build(RecoupConfig(db=":memory:", llm="fake"))
    assert app.runtime_provider == "engine"
    try:
        yield app
    finally:
        app.world.close()


def proposed(service, case_id, kind):
    return next(
        p
        for p in service.world.view(case_id).proposals
        if p.kind == kind and p.status == "proposed"
    )


def submit(service, proposal):
    approval = service.approve(proposal.proposal_id, proposal.version, "SYNTHETIC reviewer")
    receipt = service.submit(proposal.proposal_id, proposal.version)
    assert approval.proposal_version == receipt.proposal_version == proposal.version
    assert approval.draft_sha256 == proposal.draft_sha256
    assert receipt.receipt_id.startswith("MOCK-")
    return receipt


def test_published_hero_facade_edit_correction_followup_notice_and_blocked_claim(service):
    """Design/01 §10: each mutation dispatches through the public facade."""
    service.load([str(ROOT / "cases/demo/H")])
    world = service.world
    assert world.ledger_balance("H").cents == 624000
    credit = submit(service, proposed(service, "H", "credit_memo"))
    assert credit.amount.cents == 180000
    assert world.ledger_balance("H").cents == 444000

    dispute = proposed(service, "H", "dispute")
    edited = service.edit(
        dispute.proposal_id,
        dispute.version,
        draft_text=dispute.draft_text + " SYNTHETIC reviewer: please review these cited records.",
    )
    assert edited.version == dispute.version + 1
    original = submit(service, edited)
    assert original.amount.cents == 444000
    assert original.proposal_id == edited.proposal_id
    original_snapshot = original.model_dump(mode="json")

    service.advance(days=3)
    current = world.view("H")
    assert [
        (line.line_id, line.valid.cents, line.disputed.cents) for line in current.decision.lines
    ] == [
        ("D1", 312000, 0),
        ("D2", 180000, 132000),
    ]
    correction = proposed(service, "H", "correction")
    incremental = proposed(service, "H", "credit_memo")
    assert correction.corrects_receipt_id == original.receipt_id
    assert correction.amount.cents == incremental.amount.cents == 312000
    assert [a.line_id for a in incremental.allocations] == ["D1"]
    submit(service, correction)
    submit(service, incremental)
    assert world.ledger_balance("H").cents == 132000
    before = world.ledger("H")
    assert (
        service.submit(edited.proposal_id, edited.version).model_dump(mode="json")
        == original_snapshot
    )
    assert world.ledger("H") == before
    assert len(world.view("H").receipts) == 4
    credits = [r for r in world.view("H").receipts if ":credit_memo:" in r.business_key]
    assert sorted(r.amount.cents for r in credits) == [180000, 312000]

    service.advance(days=14)
    assert world.clock.day() == 17
    submit(service, proposed(service, "H", "follow_up"))
    service.advance(days=18)
    assert world.clock.day() == 35
    notice = proposed(service, "H", "insurer_notice")
    assert notice.balance_basis.cents == 132000
    submit(service, notice)
    service.advance(days=60)
    assert world.clock.day() == 95
    claim = next(
        r for r in reversed(world.readiness("H")) if r.kind == "claim" and r.status != "stale"
    )
    items = {item.item_id: item.status for item in claim.items}
    assert claim.status == "not_ready"
    assert items["claim.waiting_period"] == "present"
    assert items["claim.collection_history"] == "present"
    assert items["claim.doc.4"] == "missing"
    assert items["claim.disputed_portion"] == "restricted"
    package = proposed(service, "H", "claim_package")
    service.approve(package.proposal_id, package.version, "SYNTHETIC reviewer")
    with pytest.raises(GateError, match="claim_not_ready"):
        service.submit(package.proposal_id, package.version)
    assert len(world.view("H").receipts) == 6
    assert world.ledger_balance("H").cents == 132000
    assert (
        next(r for r in world.view("H").receipts if r.receipt_id == original.receipt_id).model_dump(
            mode="json"
        )
        == original_snapshot
    )


@pytest.mark.parametrize(
    "case_id,kind,balance", [("C", "credit_memo", 0), ("N", "info_request", 215000)]
)
def test_concede_and_unexplained_facade_submit_only_supported_action(
    service, case_id, kind, balance
):
    service.load([str(ROOT / f"cases/demo/{case_id}")])
    view = service.world.view(case_id)
    assert {p.kind.value for p in view.proposals if p.status == "proposed"} == {kind}
    proposal = proposed(service, case_id, kind)
    receipt = submit(service, proposal)
    assert service.submit(proposal.proposal_id, proposal.version) == receipt
    assert len(service.world.view(case_id).receipts) == 1
    assert service.world.ledger_balance(case_id).cents == balance


def test_real_financial_facade_offer_receipt_and_remittance_conservation(service):
    service.load([str(ROOT / "cases/ambition/counteroffer")])
    offer = proposed(service, "COUNTEROFFER", "counteroffer")
    assert offer.offer_ref == "A/B" and offer.amount.cents == 10000
    before = service.world.ledger("COUNTEROFFER")
    receipt = submit(service, offer)
    assert receipt.offer_ref == "A/B"
    assert service.submit(offer.proposal_id, offer.version) == receipt
    assert service.world.ledger("COUNTEROFFER") == before
    path = str(ROOT / "cases/ambition/multi-invoice/remittance.json")
    result = service.load_remittance(path)
    assert result.status == "loaded"
    assert sum(a.amount.cents for a in result.allocations) + result.unapplied.cents == 23000
    assert service.world.ledger_balance("ALLOC-A").cents == 0
    assert service.world.ledger_balance("ALLOC-B").cents == 5000
    balances = {cid: service.world.ledger(cid) for cid in ["COUNTEROFFER", "ALLOC-A", "ALLOC-B"]}
    assert service.load_remittance(path).replay
    assert {cid: service.world.ledger(cid) for cid in balances} == balances


def test_unsent_approved_dispute_is_voided_then_replaced_without_correction(service):
    """The published H unsent variant cascades through actual SQLite and facade."""
    service.load([str(ROOT / "cases/demo/H")])
    submit(service, proposed(service, "H", "credit_memo"))
    old = proposed(service, "H", "dispute")
    approval = service.approve(old.proposal_id, old.version, "SYNTHETIC reviewer")
    service.advance(days=3)
    history = service.history("H")
    old_saved = next(
        p
        for p in history.proposals_all
        if (p.proposal_id, p.version) == (old.proposal_id, old.version)
    )
    assert old_saved.status == "stale"
    assert next(a for a in history.approvals if a.approval_id == approval.approval_id).void
    with pytest.raises(GateError, match="not_approved|stale"):
        service.submit(old.proposal_id, old.version)
    replacement = proposed(service, "H", "dispute")
    assert replacement.amount.cents == 132000
    assert [a.line_id for a in replacement.allocations] == ["D2"]
    assert not any(p.kind == "correction" for p in service.world.view("H").proposals)
    assert len(service.world.view("H").receipts) == 1
