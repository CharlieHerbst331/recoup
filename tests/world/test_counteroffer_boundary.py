"""Independent World financial defenses even when the engine validator passes."""

from urllib.parse import quote

import pytest

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import (
    Citation,
    Decision,
    FieldTrust,
    LineAmount,
    LineDecision,
    Proposal,
)
from recoup.contracts.money import Money


def setup(
    world, bundle, *, authority=1200, amount=700, sender="buyer@example.test", expires="2026-10-30"
):
    bundle.allowed_recipients["mock_buyer_portal"] = ["buyer@example.test"]
    bundle.docs.extend(
        [
            BundleDoc(
                doc_ref="COMPANY",
                kind="company_policy",
                title="SYNTHETIC authority",
                fields={"authority_cents": authority},
            ),
            BundleDoc(
                doc_ref="OFFER",
                kind="email",
                title="SYNTHETIC buyer offer",
                fields={
                    "from": sender,
                    "offer.A/B.line.U1.concession_cents": amount,
                    "offer.A/B.expires_date": expires,
                    "offer.SECOND.line.U1.concession_cents": amount,
                    "offer.SECOND.expires_date": expires,
                },
            ),
        ]
    )
    world.load_bundle(bundle)
    decide(world)


def decide(world, *, disputed=2000, valid=0, basis="proven", verdict="invalid"):
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
                    verdict=verdict,
                    basis=basis,
                    valid=Money(cents=valid),
                    disputed=Money(cents=disputed),
                    citations=[],
                    rationale="Test",
                )
            ],
            model_id="fake",
            llm_mode="fake",
            prompt_version="test",
            created_at=world.clock.now(),
        )
    )


def proposal(world, *, ref="A/B", amount=700):
    decision = world.current_decision("CASE")
    return Proposal(
        proposal_id=f"P-{ref}",
        business_key=f"CASE:counteroffer:U1:offer:{quote(ref, safe='')}",
        version=1,
        case_id="CASE",
        kind="counteroffer",
        target="mock_buyer_portal",
        recipient="buyer@example.test",
        allocations=[LineAmount(line_id="U1", amount=Money(cents=amount))],
        amount=Money(cents=amount),
        draft_text="SYNTHETIC conditional MOCK concession offer.",
        draft_sha256="",
        citations=[fact.citation for fact in world.fact_set("CASE").facts],
        decision_id=decision.decision_id,
        decision_version=decision.version,
        evidence_set_hash=world.evidence_set_hash("CASE"),
        offer_ref=ref,
        status="proposed",
        created_at=world.clock.now(),
        created_by="agent",
    )


def post(world, p):
    saved = world.save_proposal(p)
    world.approve(saved.proposal_id, saved.version, "Charles")
    return saved, world.submit(saved.proposal_id, saved.version)


def test_offer_receipt_reserves_authority_without_posting_ledger(world, bundle):
    setup(world, bundle)
    before = world.ledger("CASE")
    p, receipt = post(world, proposal(world))
    assert receipt.offer_ref == "A/B" and receipt.amount.cents == 700
    assert world.history("CASE").approvals[0].offer_ref == "A/B"
    assert world.ledger("CASE") == before
    assert world.submit(p.proposal_id, p.version) == receipt
    with pytest.raises(GateError, match="counteroffer_authority"):
        world.save_proposal(proposal(world, ref="SECOND"))


@pytest.mark.parametrize(
    "mutation, code",
    [
        ("sender", "invalid_offer_source"),
        ("expiry", "expired_offer"),
        ("amount", "counteroffer_amount"),
        ("authority", "counteroffer_authority"),
        ("line", "counteroffer_disputed"),
        ("citation", "missing_offer_citation"),
        ("ref", "invalid_offer_source"),
        ("target", "invalid_counteroffer"),
    ],
)
def test_counteroffer_fails_closed_without_engine_validator(world, bundle, mutation, code):
    setup(
        world,
        bundle,
        sender="stranger@example.test" if mutation == "sender" else "buyer@example.test",
        expires="2026-10-01" if mutation == "expiry" else "2026-10-30",
        authority=100 if mutation == "authority" else 1200,
    )
    if mutation == "line":
        decide(world, disputed=500)
    p = proposal(world, ref="missing" if mutation == "ref" else "A/B")
    if mutation == "amount":
        p.amount = Money(cents=600)
        p.allocations[0].amount = Money(cents=600)
    elif mutation == "citation":
        p.citations = []
    elif mutation == "target":
        p.target = "mock_erp"
    with pytest.raises(GateError, match=code):
        world.save_proposal(p)
    assert not world.history("CASE").proposals_all
    assert not world.history("CASE").receipts
    assert world.ledger_balance("CASE").cents == 2000


@pytest.mark.parametrize("trust", ["ocr", "vision", "model_extracted"])
def test_unconfirmed_money_cannot_authorize_offer(world, bundle, trust):
    setup(world, bundle)
    email = next(e for e in world.active_evidence("CASE") if e.doc_ref == "OFFER")
    key = "offer.A/B.line.U1.concession_cents"
    citation = Citation(evidence_id=email.evidence_id, locator=f"fields.{key}", quote="700")
    world.add_fact(email.evidence_id, key, 700, FieldTrust(trust), citation, "test")
    decide(world)
    with pytest.raises(GateError, match="untrusted_offer"):
        world.save_proposal(proposal(world))
    world.confirm_field(email.evidence_id, key, "Charles")
    decide(world)
    assert post(world, proposal(world))[1].amount.cents == 700


def test_human_lowered_edit_bound_approval_and_cumulative_line_capacity(world, bundle):
    setup(world, bundle, authority=2000)
    saved = world.save_proposal(proposal(world))
    edited = world.edit_proposal(
        saved.proposal_id,
        saved.version,
        allocations=[LineAmount(line_id="U1", amount=Money(cents=500))],
    )
    assert edited.version == 2 and edited.amount.cents == 500
    assert edited.offer_ref == saved.offer_ref and edited.business_key == saved.business_key
    world.approve(edited.proposal_id, edited.version, "Charles")
    approved = world._proposal(edited.proposal_id, edited.version)
    world._write_proposal(approved.model_copy(update={"offer_ref": "SECOND"}))
    with pytest.raises(GateError, match="approval_mismatch"):
        world.submit(edited.proposal_id, edited.version)
    world._write_proposal(approved)
    assert world.submit(edited.proposal_id, edited.version).amount.cents == 500
    decide(world, disputed=1000)
    with pytest.raises(GateError, match="counteroffer_disputed"):
        world.save_proposal(proposal(world, ref="SECOND"))


def test_approval_rechecks_expiry_and_existing_approved_offers_recheck_cap(world, bundle):
    setup(world, bundle)
    first = world.save_proposal(proposal(world))
    second = world.save_proposal(proposal(world, ref="SECOND"))
    world.approve(first.proposal_id, first.version, "Charles")
    world.approve(second.proposal_id, second.version, "Charles")
    world.submit(first.proposal_id, first.version)
    with pytest.raises(GateError, match="counteroffer_authority"):
        world.submit(second.proposal_id, second.version)
    assert len(world.history("CASE").receipts) == 1


def test_conflicting_expiry_and_policy_authority_cannot_be_chosen(world, bundle):
    setup(world, bundle)
    world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="OTHER-OFFER",
            kind="email",
            title="Conflicting",
            fields={
                "from": "buyer@example.test",
                "offer.A/B.line.U1.concession_cents": 700,
                "offer.A/B.expires_date": "2026-11-30",
            },
        ),
    )
    decide(world)
    with pytest.raises(GateError, match="invalid_offer_source"):
        world.save_proposal(proposal(world))


@pytest.mark.parametrize("citation_kind", ["absent", "fake", "wrong-value"])
def test_world_rejects_ungrounded_facts_before_factset_exposure(world, bundle, citation_kind):
    world.load_bundle(bundle)
    evidence = next(e for e in world.active_evidence("CASE") if e.doc_ref == "POD")
    citation = (
        None
        if citation_kind == "absent"
        else Citation(
            evidence_id=evidence.evidence_id,
            locator="text",
            quote="invented quote" if citation_kind == "fake" else "Received 80 cases.",
        )
    )
    before = world.fact_set("CASE")
    with pytest.raises(GateError, match="invalid_citation"):
        world.add_fact(
            evidence.evidence_id,
            "received.SKU",
            9000,
            FieldTrust.model_extracted,
            citation,
            "model",
        )
    assert world.fact_set("CASE") == before
    assert not world.history("CASE").facts


def test_offer_selector_cannot_be_reused_with_a_different_line_key(world, bundle):
    setup(world, bundle, authority=5000)
    post(world, proposal(world))
    # Selector identity survives a new admissible decision.
    decide(world, disputed=2000)
    repeated = proposal(world)
    repeated.business_key += "-different"
    repeated.proposal_id = "NEW-ID"
    with pytest.raises(GateError, match="invalid_counteroffer"):
        world.save_proposal(repeated)
    # Boundary itself checks selector reuse before any second receipt independently of business_key.
    with pytest.raises(GateError, match="offer_already_submitted"):
        world._counteroffer_guard(proposal(world), {"U1": 700})
    assert len(world.history("CASE").receipts) == 1


def test_approval_rechecks_expired_offer_in_simulated_clock(world, bundle):
    setup(world, bundle, expires="2026-10-20")
    saved = world.save_proposal(proposal(world))
    world.db.execute("UPDATE meta SET value='1' WHERE key='sim_day'")
    with pytest.raises(GateError, match="expired_offer"):
        world.approve(saved.proposal_id, saved.version, "Charles")
    assert not world.history("CASE").approvals


def test_zero_aggregate_and_line_removal_cannot_consume_offer(world, bundle):
    setup(world, bundle)
    saved = world.save_proposal(proposal(world))
    with pytest.raises(GateError, match="invalid_counteroffer"):
        world.edit_proposal(
            saved.proposal_id,
            saved.version,
            allocations=[LineAmount(line_id="U1", amount=Money(cents=0))],
        )
    with pytest.raises(GateError, match="counteroffer_lines"):
        world.edit_proposal(saved.proposal_id, saved.version, allocations=[])
    assert not world.history("CASE").receipts


def test_source_field_fact_cannot_claim_different_value_or_type(world, bundle):
    world.load_bundle(bundle)
    evidence = next(e for e in world.active_evidence("CASE") if e.doc_ref == "PAY")
    citation = Citation(evidence_id=evidence.evidence_id, locator="fields.paid_cents", quote="8000")
    for value in ["8000", 9000, True]:
        with pytest.raises(GateError, match="invalid_citation"):
            world.add_fact(
                evidence.evidence_id,
                "paid_cents",
                value,
                FieldTrust.human_confirmed,
                citation,
                "human",
            )
    assert world.ledger_balance("CASE").cents == 2000
    assert world.fact_set("CASE").buyer_senders == ["buyer@example.test"]


def test_human_zero_line_retains_key_and_offer_cannot_replay_on_other_subset(world, bundle):
    setup(world, bundle, authority=5000)
    world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="LINES",
            kind="debit_memo",
            title="SYNTHETIC lines",
            fields={
                "ded.1.line_id": "D1",
                "ded.1.claimed_cents": 1000,
                "ded.2.line_id": "D2",
                "ded.2.claimed_cents": 1000,
            },
        ),
    )
    world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="OFFER",
            version=2,
            kind="email",
            title="Buyer offer",
            fields={
                "from": "buyer@example.test",
                "offer.A/B.expires_date": "2026-10-30",
                "offer.A/B.line.D1.concession_cents": 300,
                "offer.A/B.line.D2.concession_cents": 400,
            },
        ),
    )
    decision = decide(world)
    decision = decision.model_copy(
        update={
            "lines": [
                decision.lines[0].model_copy(
                    update={"line_id": line, "disputed": Money(cents=1000)}
                )
                for line in ["D1", "D2"]
            ]
        }
    )
    world.save_decision(decision)
    p = proposal(world)
    p.business_key = "CASE:counteroffer:D1+D2:offer:A%2FB"
    p.allocations = [
        LineAmount(line_id="D1", amount=Money(cents=300)),
        LineAmount(line_id="D2", amount=Money(cents=400)),
    ]
    saved = world.save_proposal(p)
    edited = world.edit_proposal(
        saved.proposal_id,
        saved.version,
        allocations=[
            LineAmount(line_id="D1", amount=Money(cents=0)),
            LineAmount(line_id="D2", amount=Money(cents=400)),
        ],
    )
    assert edited.business_key == saved.business_key
    world.approve(edited.proposal_id, edited.version, "Charles")
    receipt = world.submit(edited.proposal_id, edited.version)
    assert [a.amount.cents for a in receipt.allocations] == [0, 400]
    subset = proposal(world)
    subset.proposal_id = "P-SUBSET"
    subset.business_key = "CASE:counteroffer:D1:offer:A%2FB"
    subset.amount = Money(cents=300)
    subset.allocations = [LineAmount(line_id="D1", amount=Money(cents=300))]
    with pytest.raises(GateError, match="offer_already_submitted"):
        world.save_proposal(subset)
    assert world.ledger_balance("CASE").cents == 2000


def test_identical_offer_save_rechecks_expiry_instead_of_noop(world, bundle):
    setup(world, bundle, expires="2026-10-20")
    saved = world.save_proposal(proposal(world))
    world.db.execute("UPDATE meta SET value='1' WHERE key='sim_day'")
    with pytest.raises(GateError, match="expired_offer"):
        world.save_proposal(saved)
