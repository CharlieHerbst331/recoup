"""Published synthetic financial examples through real app assembly."""

from pathlib import Path

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import CaseBundle
from recoup.contracts.testing import NullController

ROOT = Path(__file__).resolve().parents[2] / "cases/ambition"


def test_remittance_facade_allocates_then_replay_does_not_react():
    class Counted(NullController):
        def __init__(self):
            self.calls = 0

        def react(self, *args):
            self.calls += 1

    controller = Counted()
    service = build(RecoupConfig(db=":memory:"), controller=controller)
    try:
        path = str(ROOT / "multi-invoice/remittance.json")
        result = service.load_remittance(path)
        assert result.status == "loaded"
        assert [a.amount.cents for a in result.allocations] == [10000, 10000]
        assert result.unapplied.cents == 3000
        assert service.world.ledger_balance("ALLOC-A").cents == 0
        assert service.world.ledger_balance("ALLOC-B").cents == 5000
        assert controller.calls == 1
        assert service.load_remittance(path).replay
        assert controller.calls == 1
    finally:
        service.world.close()


def test_counteroffer_fixture_has_proven_dispute_and_resolvable_offer():
    service = build(RecoupConfig(db=":memory:"))
    try:
        path = ROOT / "counteroffer/bundle.json"
        bundle = CaseBundle.model_validate_json(path.read_text())
        assert service.world.load_bundle(bundle).status == "loaded"
        service.run(bundle.case_id)
        decision = service.world.current_decision(bundle.case_id)
        line = next(line for line in decision.lines if line.line_id == "D2")
        assert line.verdict == "invalid"
        assert line.basis == "proven"
        assert line.disputed.cents == 50000
        facts = service.world.fact_set(bundle.case_id)
        offer = next(f for f in facts.facts if f.key == "offer.A/B.line.D2.concession_cents")
        assert offer.value == 10000
        assert service.world.resolve_citation(offer.citation)
        assert "buyer@example.invalid" in facts.buyer_senders
    finally:
        service.world.close()
