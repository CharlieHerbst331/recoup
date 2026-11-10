"""Engine financial consumers through app-built SQLite; design/02 §5.4–5.5."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import LineAmount
from recoup.contracts.money import Money
from recoup.contracts.testing import NullController
from recoup.engine.counteroffers import derive_counteroffer
from recoup.engine.gates import ProposalValidator
from recoup.engine.harness import HarnessEngine, _draft_args
from recoup.engine.llm import FakeLLM
from recoup.engine.tools import ToolSessionFactory

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bundle():
    return CaseBundle.model_validate_json(
        (ROOT / "cases/ambition/counteroffer/bundle.json").read_text()
    )


@pytest.fixture
def world():
    service = build(RecoupConfig(db=":memory:"), controller=NullController())
    yield service.world
    service.world.close()


def investigate(world, bundle):
    world.load_bundle(bundle)
    view = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "ambition")
    assert view.status != "needs_human", view.status_reason
    return view


def draft(world, ref="A/B", ids=None):
    p = derive_counteroffer(world, "COUNTEROFFER", ids or ["D2"], ref)
    args = _draft_args(world, p, "fake")
    result = (
        ToolSessionFactory().open(world, p.case_id, "test", "harness").call("draft_proposal", args)
    )
    assert result.ok, result
    assert result.result["accepted"], result
    return next(
        p
        for p in world.view(p.case_id).proposals
        if p.business_key == result.result["business_key"]
    )


def post(world, p):
    world.approve(p.proposal_id, p.version, "SYNTHETIC reviewer")
    return world.submit(p.proposal_id, p.version)


def test_fake_completion_approval_mock_receipt_and_duplicate(world, bundle):
    view = investigate(world, bundle)
    p = next(p for p in view.proposals if p.kind == "counteroffer")
    assert p.offer_ref == "A/B" and p.amount.cents == 10000
    assert p.business_key.endswith(":D2:offer:A%2FB")
    assert any(p.kind == "credit_memo" for p in view.proposals)
    before = world.ledger(bundle.case_id)
    receipt = post(world, p)
    assert receipt.offer_ref == "A/B" and receipt.receipt_id.startswith("MOCK-")
    assert world.submit(p.proposal_id, p.version) == receipt
    assert world.ledger(bundle.case_id) == before
    HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "repeat")
    assert len(world.view(bundle.case_id).receipts) == 1


@pytest.mark.parametrize("authority", [10000, 10001, 9999])
def test_authority_boundary(world, bundle, authority):
    next(d for d in bundle.docs if d.kind == "company_policy").fields["authority_cents"] = authority
    investigate(world, bundle)
    if authority < 10000:
        with pytest.raises(GateError, match="counteroffer_authority"):
            derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")
    else:
        assert post(world, draft(world)).amount.cents == 10000


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_authority",
        "conflict_authority",
        "missing_expiry",
        "expired",
        "sender",
        "zero",
        "bool",
        "conflict_offer",
        "partial_offer",
        "over_line",
        "missing_offer",
    ],
)
def test_evidence_fails_closed_in_engine(world, bundle, mutation):
    policy = next(d for d in bundle.docs if d.kind == "company_policy")
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    if mutation == "missing_authority":
        del policy.fields["authority_cents"]
    elif mutation == "conflict_authority":
        bundle.docs.append(
            BundleDoc(
                doc_ref="OTHER-POLICY",
                kind="company_policy",
                title="SYNTHETIC",
                fields={"authority_cents": 99999},
            )
        )
    elif mutation == "missing_expiry":
        del offer.fields["offer.A/B.expires_date"]
    elif mutation == "expired":
        offer.fields["offer.A/B.expires_date"] = "2026-10-19"
    elif mutation == "sender":
        offer.fields["from"] = "stranger.invalid"
    elif mutation in {"zero", "bool", "over_line"}:
        offer.fields["offer.A/B.line.D2.concession_cents"] = {
            "zero": 0,
            "bool": True,
            "over_line": 50001,
        }[mutation]
    elif mutation in {"conflict_offer", "partial_offer"}:
        fields = dict(offer.fields)
        if mutation == "partial_offer":
            del fields["offer.A/B.expires_date"]
        else:
            fields["offer.A/B.line.D2.concession_cents"] = 9000
        bundle.docs.append(
            BundleDoc(doc_ref="OTHER-OFFER", kind="email", title="SYNTHETIC", fields=fields)
        )
    else:
        bundle.docs.remove(offer)
    investigate(world, bundle)
    with pytest.raises(GateError):
        derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")
    assert not any(p.kind == "counteroffer" for p in world.view(bundle.case_id).proposals)


@pytest.mark.parametrize("trust", ["ocr", "vision", "model_extracted"])
@pytest.mark.parametrize("source", ["BUYER-OFFER", "COMPANY"])
def test_untrusted_money_and_confirmation(world, bundle, trust, source):
    investigate(world, bundle)
    fact = next(
        f
        for f in world.fact_set(bundle.case_id).facts
        if f.doc_ref == source
        and f.key.endswith("cents")
        and (f.key == "authority_cents" or f.key.startswith("offer."))
    )
    world.add_fact(fact.evidence_id, fact.key, fact.value, trust, fact.citation, "SYNTHETIC")
    HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "untrusted")
    with pytest.raises(GateError, match="untrusted_offer"):
        derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")
    world.confirm_field(fact.evidence_id, fact.key, "SYNTHETIC")
    HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "confirmed")
    assert post(world, draft(world)).amount.cents == 10000


def test_competing_approvals_and_lifetime_reservations(world, bundle):
    next(d for d in bundle.docs if d.kind == "company_policy").fields["authority_cents"] = 15000
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    offer.fields.update(
        {"offer.SECOND.line.D2.concession_cents": 10000, "offer.SECOND.expires_date": "2026-10-30"}
    )
    investigate(world, bundle)
    first, second = draft(world), draft(world, "SECOND")
    for p in [first, second]:
        world.approve(p.proposal_id, p.version, "SYNTHETIC")
    receipt = world.submit(first.proposal_id, first.version)
    issues = ProposalValidator().validate(world, second, "submit")
    assert "counteroffer_authority" in {i.code for i in issues}
    with pytest.raises(GateError):
        world.submit(second.proposal_id, second.version)
    assert world.view(bundle.case_id).receipts == [receipt]


def test_expiry_rechecked_at_approve_and_submit(world, bundle):
    next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER").fields["offer.A/B.expires_date"] = (
        "2026-10-20"
    )
    investigate(world, bundle)
    p = draft(world)
    world.approve(p.proposal_id, p.version, "SYNTHETIC")
    world.advance_to(1, release_events=False)
    for stage in ["approve", "submit"]:
        assert "expired_offer" in {i.code for i in ProposalValidator().validate(world, p, stage)}
        with pytest.raises(GateError):
            getattr(world, stage)(
                p.proposal_id, p.version, *(["SYNTHETIC"] if stage == "approve" else [])
            )


def test_human_downward_edit_and_missing_citations(world, bundle):
    investigate(world, bundle)
    p = draft(world)
    invalid = p.model_copy(update={"citations": []})
    assert "missing_offer_citation" in {
        i.code for i in ProposalValidator().validate(world, invalid, "save")
    }
    edited = world.edit_proposal(
        p.proposal_id, p.version, allocations=[LineAmount(line_id="D2", amount=Money(cents=5000))]
    )
    receipt = post(world, edited)
    assert receipt.amount.cents == 5000 and receipt.offer_ref == "A/B"
    with pytest.raises(GateError, match="offer_already_submitted"):
        derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")


def test_multi_invoice_handler_consumes_shared_intake(bundle):
    service = build(RecoupConfig(db=":memory:"))
    try:
        bundle.case_id = "UNRELATED"
        service.world.load_bundle(bundle)
        service.run("UNRELATED")
        unrelated = service.world.view("UNRELATED")
        result = service.load_remittance(str(ROOT / "cases/ambition/multi-invoice/remittance.json"))
        assert result.status == "loaded"
        assert service.world.view("UNRELATED") == unrelated
        assert service.world.ledger_balance("ALLOC-A").cents == 0
        assert service.world.ledger_balance("ALLOC-B").cents == 5000
        for cid in ["ALLOC-A", "ALLOC-B"]:
            assert service.world.current_decision(cid) is not None
        before = service.world.history("ALLOC-A")
        assert service.load_remittance(
            str(ROOT / "cases/ambition/multi-invoice/remittance.json")
        ).replay
        assert service.world.history("ALLOC-A") == before
    finally:
        service.world.close()


def test_exact_punctuation_multi_line_zero_edit_and_reference_replay(world, bundle):
    rem = next(d for d in bundle.docs if d.kind == "remittance")
    rem.fields.update({"ded.1.line_id": "D.1/x", "ded.1.reason": "pricing", "ded.1.sku": "SKU-7"})
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    offer.fields = {
        "from": "buyer@example.invalid",
        "offer.R./x.expires_date": "2026-10-30",
        "offer.R./x.line.D.1/x.concession_cents": 1000,
        "offer.R./x.line.D2.concession_cents": 2000,
    }
    investigate(world, bundle)
    p = draft(world, "R./x", ["D.1/x", "D2"])
    assert p.business_key.endswith(":D.1/x+D2:offer:R.%2Fx")
    for amounts in [
        [],
        [LineAmount(line_id="D2", amount=Money(cents=1000))],
        [
            LineAmount(line_id="D.1/x", amount=Money(cents=0)),
            LineAmount(line_id="D2", amount=Money(cents=0)),
        ],
    ]:
        with pytest.raises(GateError):
            world.edit_proposal(p.proposal_id, p.version, allocations=amounts)
    edited = world.edit_proposal(
        p.proposal_id,
        p.version,
        allocations=[
            LineAmount(line_id="D.1/x", amount=Money(cents=0)),
            LineAmount(line_id="D2", amount=Money(cents=1500)),
        ],
    )
    receipt = post(world, edited)
    assert [a.amount.cents for a in receipt.allocations] == [0, 1500]
    assert receipt.business_key == p.business_key
    with pytest.raises(GateError, match="offer_already_submitted"):
        derive_counteroffer(world, bundle.case_id, ["D2"], "R./x")


def test_line_reservations_and_past_receipts_escalate(world, bundle):
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    offer.fields.update(
        {"offer.SECOND.line.D2.concession_cents": 45000, "offer.SECOND.expires_date": "2026-10-30"}
    )
    investigate(world, bundle)
    receipt = post(world, draft(world))
    with pytest.raises(GateError, match="counteroffer_disputed"):
        derive_counteroffer(world, bundle.case_id, ["D2"], "SECOND")
    policy = next(d for d in bundle.docs if d.kind == "company_policy").model_copy(deep=True)
    policy.version = 2
    policy.fields["authority_cents"] = 5000
    world.add_evidence(bundle.case_id, policy)
    view = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "over-reserved")
    assert view.status == "needs_human"
    assert world.view(bundle.case_id).receipts == [receipt]


def test_stale_basis_and_decision_void_approval(world, bundle):
    investigate(world, bundle)
    p = draft(world)
    world.approve(p.proposal_id, p.version, "SYNTHETIC")
    world.add_evidence(
        bundle.case_id,
        BundleDoc(
            doc_ref="NEW", kind="collection_note", title="SYNTHETIC", text="SYNTHETIC new evidence"
        ),
    )
    codes = {i.code for i in ProposalValidator().validate(world, p, "submit")}
    assert {"stale_basis", "stale_decision"} <= codes
    with pytest.raises(GateError):
        world.submit(p.proposal_id, p.version)
    assert any(a.void for a in world.history(bundle.case_id).approvals)


def test_nonpayment_cannot_negotiate(world, bundle):
    bundle.docs = [d for d in bundle.docs if d.kind not in {"payment", "remittance"}]
    bundle.docs.append(
        BundleDoc(doc_ref="POD", kind="pod", title="SYNTHETIC", fields={"signed": True})
    )
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    offer.fields["offer.A/B.line.NP.concession_cents"] = 1000
    investigate(world, bundle)
    with pytest.raises(GateError, match="counteroffer_disputed"):
        derive_counteroffer(world, bundle.case_id, ["NP"], "A/B")


@pytest.mark.parametrize(
    "field,value",
    [
        ("authority_cents", True),
        ("authority_cents", -1),
        ("authority_cents", "10000"),
        ("offer.A/B.expires_date", "2026-10-20T00:00:00"),
        ("offer.A/B.line.D2.concession_cents", "10000"),
    ],
)
def test_strict_fact_types(world, bundle, field, value):
    doc = next(
        d
        for d in bundle.docs
        if d.kind == ("company_policy" if field == "authority_cents" else "email")
    )
    doc.fields[field] = value
    investigate(world, bundle)
    with pytest.raises(GateError):
        derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")


def test_engine_rule_revalidation(world, bundle):
    investigate(world, bundle)
    p = draft(world)
    # A changed proven decision cannot manufacture negotiation capacity.
    current = world.current_decision(bundle.case_id)
    changed = current.model_copy(deep=True)
    line = next(d for d in changed.lines if d.line_id == "D2")
    line.disputed = Money(cents=49999)
    new = world.save_decision(changed)
    p = p.model_copy(update={"decision_id": new.decision_id, "decision_version": new.version})
    assert "decision_rule_mismatch" in {
        i.code for i in ProposalValidator().validate(world, p, "save")
    }


@pytest.mark.parametrize("signal,expected", [(True, "needs_human"), (False, None)])
def test_legal_review_routing(world, bundle, signal, expected):
    rem = next(d for d in bundle.docs if d.kind == "remittance")
    rem.fields["ded.2.requires_legal_review"] = signal
    world.load_bundle(bundle)
    view = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "legal")
    if expected:
        assert view.status == expected and "legal authority" in view.status_reason
    else:
        assert view.status != "needs_human"


def test_offer_open_balance_cap(world, bundle):
    bundle.docs.append(
        BundleDoc(
            doc_ref="EXTRA-PAY",
            kind="payment",
            title="SYNTHETIC",
            fields={
                "invoice_no": "INV-r01",
                "paid_cents": 65000,
                "paid_date": "2026-10-20",
                "payment_ref": "EXTRA",
            },
        )
    )
    investigate(world, bundle)
    assert world.ledger_balance(bundle.case_id).cents == 6000
    with pytest.raises(GateError, match="counteroffer_balance"):
        derive_counteroffer(world, bundle.case_id, ["D2"], "A/B")


def test_counteroffer_handler_drafts_new_buyer_offer(world, bundle):
    offer = next(d for d in bundle.docs if d.doc_ref == "BUYER-OFFER")
    bundle.docs.remove(offer)
    investigate(world, bundle)
    world.add_evidence(bundle.case_id, offer)
    HarnessEngine().handle(world, FakeLLM(), "buyer-offer")
    assert any(
        p.kind == "counteroffer" and p.status == "proposed"
        for p in world.view(bundle.case_id).proposals
    )
    HarnessEngine().handle(world, FakeLLM(), "repeat-handler")
    assert len([p for p in world.view(bundle.case_id).proposals if p.kind == "counteroffer"]) == 1


@pytest.mark.parametrize(
    "sender,has_line,expected",
    [
        ("buyer.invalid", True, "needs_info"),
        ("supplier.invalid", True, "invalid"),
        ("buyer.invalid", False, "invalid"),
    ],
)
def test_buyer_classification_requires_sender_and_line(sender, has_line, expected):
    from recoup.engine.rules import run_rules

    from .fixtures import rule_inputs
    from .test_rules import vector_named

    vector = vector_named("np_balance_owed")
    fields = {"from": sender, "ded.1.reason": "shortage"}
    if has_line:
        fields["ded.1.line_id"] = "D1"
    vector["input"]["documents"].append({"id": "buyer", "kind": "email", "fields": fields})
    lines, facts, ledger = rule_inputs(vector)
    facts.buyer_senders = ["buyer.invalid"]
    assert run_rules(lines, facts, ledger)[0].verdict == expected


def test_full_offline_h_c_n_demo():
    service = build(RecoupConfig(db=":memory:"))
    try:
        service.load([str(ROOT / f"cases/demo/{cid}") for cid in ["H", "C", "N"]])
        world = service.world

        def submit_kind(kind):
            p = next(
                p for p in world.view("H").proposals if p.kind == kind and p.status == "proposed"
            )
            receipt = post(world, p)
            service.run()
            return receipt

        submit_kind("dispute")
        submit_kind("credit_memo")
        service.advance(days=3)
        submit_kind("correction")
        submit_kind("credit_memo")
        assert world.ledger_balance("H").cents == 132000
        service.advance(days=14)
        submit_kind("follow_up")
        service.advance(days=18)
        notice = next(
            p
            for p in world.view("H").proposals
            if p.kind == "insurer_notice" and p.status == "proposed"
        )
        assert notice.balance_basis.cents == 132000
        submit_kind("insurer_notice")
        service.advance(days=60)
        package = next(
            p
            for p in world.view("H").proposals
            if p.kind == "claim_package" and p.status == "proposed"
        )
        claim = next(
            r for r in reversed(world.readiness("H")) if r.kind == "claim" and r.status != "stale"
        )
        assert claim.status == "not_ready"
        assert any(i.status == "missing" and i.item_id == "claim.doc.4" for i in claim.items)
        world.approve(package.proposal_id, package.version, "SYNTHETIC")
        with pytest.raises(GateError, match="claim_not_ready"):
            world.submit(package.proposal_id, package.version)
        assert {p.kind for p in world.view("C").proposals} == {"credit_memo"}
        assert {p.kind for p in world.view("N").proposals} == {"info_request"}
    finally:
        service.world.close()


@pytest.mark.parametrize("mode", ["readable", "unreadable", "conflict", "untrusted"])
def test_legal_inventory_conflict_and_trust(world, bundle, mode):
    rem = next(d for d in bundle.docs if d.kind == "remittance")
    rem.fields["ded.2.requires_legal_review"] = True
    if mode in {"readable", "unreadable"}:
        bundle.docs.append(
            BundleDoc(
                doc_ref="LEGAL",
                kind="legal_authority",
                title="SYNTHETIC",
                text="SYNTHETIC case authority" if mode == "readable" else "",
                file="missing.pdf" if mode == "unreadable" else None,
            )
        )
    elif mode == "conflict":
        bundle.docs.append(
            BundleDoc(
                doc_ref="OTHER-LEGAL-SIGNAL",
                kind="email",
                title="SYNTHETIC",
                fields={
                    "from": "buyer@example.invalid",
                    "ded.1.line_id": "D2",
                    "ded.1.reason": "pricing",
                    "ded.1.requires_legal_review": False,
                },
            )
        )
    world.load_bundle(bundle)
    if mode == "untrusted":
        fact = next(
            f
            for f in world.fact_set(bundle.case_id).facts
            if f.key == "ded.2.requires_legal_review"
        )
        world.add_fact(fact.evidence_id, fact.key, True, "ocr", fact.citation, "SYNTHETIC")
    view = HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "legal-inventory")
    assert (view.status == "needs_human") == (mode != "readable")
    if mode == "conflict":
        assert "conflicting legal" in view.status_reason
    elif mode == "untrusted":
        assert "human confirmation" in view.status_reason


def test_receipt_event_preserves_followup_already_scheduled_by_investigation(world, bundle):
    view = investigate(world, bundle)
    receipt = post(world, next(p for p in view.proposals if p.kind == "dispute"))
    HarnessEngine().investigate(world, bundle.case_id, FakeLLM(), "scoped-run")
    before = next(
        d
        for d in world.view(bundle.case_id).due
        if d.kind == "follow_up" and d.basis == receipt.receipt_id
    )
    assert before.status == "pending"
    HarnessEngine().handle(world, FakeLLM(), "receipt-event")
    after = next(d for d in world.view(bundle.case_id).due if d.due_id == before.due_id)
    assert after.status == "pending"
    world.advance_to(14)
    HarnessEngine().handle(world, FakeLLM(), "due")
    assert len([p for p in world.view(bundle.case_id).proposals if p.kind == "follow_up"]) == 1
