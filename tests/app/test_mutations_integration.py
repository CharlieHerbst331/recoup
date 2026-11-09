"""Real World and explicit validator stub: §4.5 controller orchestration only."""

from datetime import timedelta

import pytest

from recoup.contracts.bundle import BundleDoc, BundleEvent
from recoup.contracts.models import (
    Basis,
    Decision,
    DocKind,
    LineAmount,
    LineDecision,
    Proposal,
    ProposalKind,
    ProposalStatus,
    Target,
    Verdict,
)
from recoup.contracts.money import Money

from .test_build_integration import synthetic_bundle


@pytest.fixture(autouse=True)
def contract_stub_runtime(monkeypatch):
    import recoup.app as module

    # The fabricated decision below tests routing, never real financial gates.
    monkeypatch.setattr(module, "find_spec", lambda name: None)


@pytest.mark.parametrize("name", ["null", "scripted-T-min", "REF", "BAD"])
def test_real_mutations_only_dispatch_once_to_selected_controller(tmp_path, monkeypatch, name):
    from recoup.app import RecoupConfig, build
    from recoup.contracts.testing import StubEngine

    def forbidden(*args, **kwargs):
        raise AssertionError("Facade invoked harness under a custom controller")

    monkeypatch.setattr(StubEngine, "investigate", forbidden)
    monkeypatch.setattr(StubEngine, "handle", forbidden)

    class Controller:
        def __init__(self):
            self.name = name
            self.calls = []

        def react(self, world, events, run_id):
            self.calls.append((world.clock.day(), [event.type for event in events], run_id))

    bundle = synthetic_bundle()
    bundle.allowed_recipients = {"mock_erp": ["erp"], "mock_email": ["buyer@example.test"]}
    bundle.events = [
        BundleEvent(
            at_day=2,
            type="add_doc",
            doc=BundleDoc(
                doc_ref="reply",
                kind=DocKind.email,
                title="SYNTHETIC reply",
                text="Please send proof.",
            ),
        )
    ]
    (tmp_path / "bundle.json").write_text(bundle.model_dump_json())
    controller = Controller()
    service = build(RecoupConfig(db=":memory:", run_id="ISOLATION"), controller=controller)
    world = service.world
    service.load([str(tmp_path)])
    service.run(bundle.case_id)
    service.advance(days=1)
    service.advance(days=1)
    evidence = service.add_evidence(
        bundle.case_id,
        BundleDoc(doc_ref="POD", kind=DocKind.pod, title="SYNTHETIC POD", fields={"signed": True}),
    )
    service.confirm_field(evidence.evidence_id, "signed")
    decision = world.save_decision(
        Decision(
            decision_id="DEC-ISOLATION",
            case_id=bundle.case_id,
            version=1,
            evidence_set_hash=world.evidence_set_hash(bundle.case_id),
            lines=[
                LineDecision(
                    line_id="U1",
                    verdict=Verdict.valid,
                    basis=Basis.proven,
                    valid=Money(cents=2000),
                    disputed=Money(cents=0),
                    citations=[],
                    rationale="SYNTHETIC controller isolation only",
                )
            ],
            current=True,
            model_id="unit-validator",
            llm_mode="fake",
            prompt_version="test",
            created_at=world.clock.now(),
        )
    )
    credit = world.save_proposal(
        Proposal(
            proposal_id="CREDIT",
            business_key=f"{bundle.case_id}:credit_memo:U1",
            version=1,
            case_id=bundle.case_id,
            kind=ProposalKind.credit_memo,
            target=Target.mock_erp,
            recipient="erp",
            allocations=[LineAmount(line_id="U1", amount=Money(cents=1000))],
            amount=Money(cents=1000),
            draft_text="SYNTHETIC mock credit",
            draft_sha256="",
            citations=[],
            decision_id=decision.decision_id,
            decision_version=decision.version,
            evidence_set_hash=decision.evidence_set_hash,
            status=ProposalStatus.proposed,
            created_at=world.clock.now(),
            created_by="agent",
        )
    )
    edited = service.edit(credit.proposal_id, credit.version, draft_text="SYNTHETIC edited credit")
    service.approve(edited.proposal_id, edited.version)
    other = world.save_proposal(
        credit.model_copy(
            update={
                "proposal_id": "REQUEST",
                "business_key": f"{bundle.case_id}:info_request:U1",
                "kind": ProposalKind.info_request,
                "target": Target.mock_email,
                "recipient": "buyer@example.test",
                "allocations": [],
                "amount": None,
            }
        )
    )
    service.reject(other.proposal_id, other.version, "SYNTHETIC rejection")
    receipt = service.submit(edited.proposal_id, edited.version)
    assert receipt.receipt_id.startswith("MOCK-")
    assert world.ledger_balance(bundle.case_id).cents == 1000
    assert world.history(bundle.case_id).attempts[-1].controller == name
    assert len(controller.calls) == 10
    assert [call[0] for call in controller.calls] == [0, 0, 1, 2, 2, 2, 2, 2, 2, 2]
    assert controller.calls[2][1] == []
    assert "evidence_added" in controller.calls[3][1]
    assert all(call[2] == "ISOLATION" for call in controller.calls)
    # The inert placeholder has no scripted model responses and is never called.
    with pytest.raises(StopIteration):
        service.llm.next("", [], [])


def test_advance_to_next_due_releases_actual_h_day_three():
    from recoup.app import RecoupConfig, build

    service = build(RecoupConfig(db=":memory:"))
    service.load(["cases/demo/H"])
    before = service.world.evidence_set_hash("H")
    assert service.next_due_day() == 3
    service.advance(to_next_due=True)
    view = service.world.view("H")
    assert view.sim_day == 3
    assert view.sim_now == service.world.clock.at_day(0) + timedelta(days=3)
    assert any(e.doc_ref == "POD" and e.version == 2 for e in view.evidence)
    assert any(e.kind == DocKind.inspection for e in view.evidence)
    assert service.world.evidence_set_hash("H") != before
    assert service.next_due_day() is None
