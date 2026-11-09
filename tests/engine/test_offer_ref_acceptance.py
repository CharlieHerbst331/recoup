"""Imported selector contracts and engine acceptance; design/02 §3.8, §5.4–5.5."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import CaseBundle
from recoup.contracts.models import Approval, LineAmount, Proposal, Receipt
from recoup.contracts.money import Money
from recoup.contracts.testing import NullController
from recoup.contracts.tools import DraftProposalArgs
from recoup.engine.counteroffers import derive_counteroffer
from recoup.engine.gates import ProposalValidator

from .test_007_8_integration import draft, investigate


@pytest.fixture
def offer_world():
    service = build(RecoupConfig(db=":memory:"), controller=NullController())
    bundle = CaseBundle.model_validate_json(
        (
            Path(__file__).resolve().parents[2] / "cases/ambition/counteroffer/bundle.json"
        ).read_text()
    )
    investigate(service.world, bundle)
    try:
        yield service.world, bundle.case_id
    finally:
        service.world.close()


def test_imported_offer_ref_contracts_and_legacy_json(offer_world):
    world, case_id = offer_world
    proposal = draft(world)
    approval = world.approve(proposal.proposal_id, proposal.version, "SYNTHETIC reviewer")
    receipt = world.submit(proposal.proposal_id, proposal.version)
    args = DraftProposalArgs(
        kind="counteroffer",
        line_ids=["D2"],
        recipient=proposal.recipient,
        draft_text=proposal.draft_text,
        citations=proposal.citations,
        offer_ref="A/B",
    )
    for model, record in [
        (Proposal, proposal),
        (Approval, approval),
        (Receipt, receipt),
        (DraftProposalArgs, args),
    ]:
        assert type(record) is model
        assert record.offer_ref == "A/B"
        assert model.model_validate_json(record.model_dump_json()).offer_ref == "A/B"
        legacy = record.model_dump(mode="json")
        del legacy["offer_ref"]
        assert model.model_validate(legacy).offer_ref is None
    assert receipt.business_key == proposal.business_key
    assert receipt.business_key.endswith(":D2:offer:A%2FB")
    assert approval.proposal_version == receipt.proposal_version == proposal.version
    assert world.view(case_id).receipts == [receipt]
    assert "amount" not in DraftProposalArgs.model_fields
    assert "allocations" not in DraftProposalArgs.model_fields


@pytest.mark.parametrize("stage", ["save", "approve", "submit"])
def test_counteroffer_engine_derivation_and_gate_acceptance(offer_world, stage):
    world, case_id = offer_world
    derived = derive_counteroffer(world, case_id, ["D2"], "A/B")
    proposal = draft(world)
    assert derived.offer_ref == proposal.offer_ref == "A/B"
    assert derived.allocations == proposal.allocations
    assert derived.amount == proposal.amount == Money(cents=10000)
    assert derived.business_key == proposal.business_key
    assert ProposalValidator().validate(world, proposal, stage) == []
    lowered = proposal.model_copy(
        update={
            "created_by": "human_edit",
            "allocations": [LineAmount(line_id="D2", amount=Money(cents=5000))],
            "amount": Money(cents=5000),
        }
    )
    assert ProposalValidator().validate(world, lowered, stage) == []
    excessive = lowered.model_copy(
        update={
            "allocations": [LineAmount(line_id="D2", amount=Money(cents=10001))],
            "amount": Money(cents=10001),
        }
    )
    assert "counteroffer_lines" in {
        issue.code for issue in ProposalValidator().validate(world, excessive, stage)
    }


@pytest.mark.parametrize("stage", ["save", "approve", "submit"])
def test_offer_ref_cannot_be_rebound_or_attached_to_other_kinds(offer_world, stage):
    world, case_id = offer_world
    proposal = draft(world)
    changed = proposal.model_copy(update={"offer_ref": "UNKNOWN", "created_by": "human_edit"})
    assert "invalid_offer_source" in {
        issue.code for issue in ProposalValidator().validate(world, changed, stage)
    }
    ordinary = next(p for p in world.view(case_id).proposals if p.kind == "credit_memo")
    assert ordinary.offer_ref is None
    changed = ordinary.model_copy(update={"offer_ref": "A/B"})
    assert "invalid_offer_ref" in {
        issue.code for issue in ProposalValidator().validate(world, changed, stage)
    }


@pytest.mark.parametrize(
    "sender,conflict", [("buyer@example.invalid", False), ("buyer-portal.invalid", True)]
)
def test_repeated_offer_requires_consistent_sender(offer_world, sender, conflict):
    from recoup.contracts.bundle import BundleDoc
    from recoup.contracts.interfaces import GateError
    from recoup.engine.tools import ToolSessionFactory

    world, case_id = offer_world
    source = next(doc for doc in world.active_evidence(case_id) if doc.doc_ref == "BUYER-OFFER")
    fields = {**source.fields, "from": sender}
    world.add_evidence(
        case_id, BundleDoc(doc_ref="REPEATED-OFFER", kind="email", title="SYNTHETIC", fields=fields)
    )
    session = ToolSessionFactory().open(world, case_id, "sender-acceptance", "test")
    findings = session.call("run_rules", {}).result["findings"]
    result = session.call(
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
    assert result.ok and result.result["accepted"]
    if conflict:
        with pytest.raises(GateError, match="invalid_offer_source"):
            derive_counteroffer(world, case_id, ["D2"], "A/B")
        current = world.current_decision(case_id)
        original = next(p for p in world.view(case_id).proposals if p.kind == "counteroffer")
        rebased = original.model_copy(
            update={
                "decision_id": current.decision_id,
                "decision_version": current.version,
                "evidence_set_hash": world.evidence_set_hash(case_id),
            }
        )
        for stage in ("save", "approve", "submit"):
            assert "invalid_offer_source" in {
                issue.code for issue in ProposalValidator().validate(world, rebased, stage)
            }
    else:
        derived = derive_counteroffer(world, case_id, ["D2"], "A/B")
        assert derived.amount.cents == 10000
        assert {c.evidence_id for c in derived.citations} >= {source.evidence_id}
