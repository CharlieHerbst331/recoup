"""007-3 independent acceptance; all data SYNTHETIC, all receipts MOCK."""

from hashlib import sha256

import pytest

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import Citation, LineAmount, Money
from recoup.contracts.tools import TOOL_REGISTRY
from recoup.engine.derive import derive, static_output
from recoup.engine.gates import ProposalValidator, assertion_issues
from recoup.engine.tools import ToolSessionFactory

from .fixtures import fact_inputs
from .tool_support import hero, replace_basis, text_world


def session(world):
    return ToolSessionFactory().open(world, world.facts.case_id, "R", "unit")


def proposal(world, kind, lines=None, **changes):
    p = next(p for p in derive(world, world.facts.case_id, lines) if p.kind == kind)
    values = dict(
        recipient="SYNTHETIC recipient", draft_text="SYNTHETIC data; MOCK action; LLM fake."
    )
    values.update(changes)
    values["draft_sha256"] = sha256(values["draft_text"].encode()).hexdigest()
    return p.model_copy(update=values)


def codes(world, p, stage="save"):
    return {i.code for i in ProposalValidator().validate(world, p, stage)}


def call(world, name, **args):
    return session(world).call(name, args)


def fact_args(value=360, key="received.SKU-1", quote="received 360 cases"):
    return dict(
        evidence_id="text-doc",
        key=key,
        value=value,
        citation=dict(evidence_id="text-doc", locator="text", quote=quote),
    )


def test_propose_fact_quote_validation_and_schema():
    w = text_world()
    s = session(w)
    assert {schema["name"] for schema in s.schemas()} == set(TOOL_REGISTRY)
    good = s.call("propose_fact", fact_args())
    assert good.ok and good.result["accepted"]
    assert w.added[0][1:4] == ("received.SKU-1", 360, "model_extracted")
    assert not s.call("propose_fact", fact_args(361)).ok
    assert not s.call("propose_fact", fact_args(36)).ok
    assert len(w.added) == 1
    assert w.traces[-1].result["ok"] is False
    assert w.traces[-1].llm_mode == "fake"
    assert w.traces[-1].controller == "unit"


@pytest.mark.parametrize("value", [7800])
@pytest.mark.parametrize("quote", ["unit price $78.00", "unit price 78.00", "unit price 7800"])
def test_money_fact_dollars_or_cents(value, quote):
    w = text_world(text="SYNTHETIC " + quote, kind="invoice")
    assert call(w, "propose_fact", **fact_args(value, "line.1.unit_price_cents", quote)).ok


@pytest.mark.parametrize("method", ["ocr", "vision"])
def test_fact_preserves_extraction_trust(method):
    w = text_world(method=method)
    result = call(w, "propose_fact", **fact_args())
    assert result.ok and result.result["trust"] == method


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"key": "made_up"}, "unknown_fact_key"),
        ({"evidence_id": "invoice"}, "invalid_citation"),
        (
            {"citation": {"evidence_id": "text-doc", "locator": "text", "quote": "fabricated 360"}},
            "invalid_citation",
        ),
        (
            {"citation": {"evidence_id": "text-doc", "locator": "text", "quote": ""}},
            "invalid_citation",
        ),
    ],
)
def test_fact_rejects_invalid_key_or_quote(change, expected):
    w = text_world()
    args = fact_args()
    args.update(change)
    result = call(w, "propose_fact", **args)
    assert not result.ok and expected in {i.code for i in result.issues}
    assert not w.added


def test_superseded_fact_and_cross_case_citations_rejected():
    w = hero()
    p = proposal(w, "dispute", ["D1"], citations=[w.facts.facts[-1].citation])
    stale = Citation(evidence_id="pod-v1", locator="fields.signed", quote="true")
    replace_basis(w, hero(after=True))
    w.inventory.append(hero().evidence("pod-v1").model_copy(update={"active": False}))
    p = p.model_copy(update={"citations": [stale]})
    assert {"superseded_citation", "stale_basis", "stale_decision"} <= codes(w, p)
    w = text_world()
    w.evidence("text-doc").case_id = "another-case"
    result = call(w, "propose_fact", **fact_args())
    assert not result.ok and result.issues[0].code == "case_scope"


@pytest.mark.parametrize("stage", ["save", "approve", "submit"])
def test_edited_credit_and_dispute_rechecked_at_all_stages(stage):
    w = hero()
    p = proposal(w, "credit_memo", ["D2"])
    assert not codes(w, p, stage)
    edited = p.model_copy(
        update={
            "created_by": "human_edit",
            "allocations": [LineAmount(line_id="D2", amount=Money(cents=180001))],
            "amount": Money(cents=180001),
        }
    )
    assert "unsupported_allocation" in codes(w, edited, stage)
    lower = edited.model_copy(
        update={
            "allocations": [LineAmount(line_id="D2", amount=Money(cents=100))],
            "amount": Money(cents=100),
        }
    )
    assert not codes(w, lower, stage)
    dispute = proposal(w, "dispute", ["D1"])
    bad = dispute.model_copy(
        update={
            "created_by": "human_edit",
            "allocations": [LineAmount(line_id="D1", amount=Money(cents=312001))],
            "amount": Money(cents=312001),
        }
    )
    assert "unsupported_allocation" in codes(w, bad, stage)


@pytest.mark.parametrize(
    "text",
    [
        "You are eligible for a payout.",
        "This confirms coverage.",
        "Your claim approval is guaranteed.",
        "We guarantee recovery.",
        "Your invoice is covered.",
        "This does not establish coverage; you are eligible for a payout.",
        "No payment is required and coverage is guaranteed.",
    ],
)
def test_assertion_check_rejects_affirmative_outcomes(text):
    assert assertion_issues(text, [])


@pytest.mark.parametrize(
    "text,citations",
    [
        ("This does not establish coverage or eligibility.", []),
        (
            'The policy says "Coverage is guaranteed".',
            [Citation(evidence_id="policy", locator="text", quote="Coverage is guaranteed")],
        ),
        ("cash collected: $0", []),
        ("We cannot guarantee recovery.", []),
    ],
)
def test_assertion_check_passes_caveats_cited_quotes_and_ledger(text, citations):
    assert not assertion_issues(text, citations)


def test_uncited_policy_quote_does_not_bypass_assertions():
    assert assertion_issues('Policy says "Coverage is guaranteed".', [])


def test_hero_correction_incremental_credit_and_no_repost():
    w = hero()
    day0 = derive(w, w.facts.case_id)
    assert {p.kind.value: p.amount.cents for p in day0} == {
        "credit_memo": 180000,
        "dispute": 444000,
    }
    for i, p in enumerate(day0, 1):
        w.record(p, i)
    assert w.ledger_balance(w.facts.case_id).cents == 444000
    assert derive(w, w.facts.case_id) == []
    replace_basis(w, hero(after=True))
    day3 = derive(w, w.facts.case_id)
    assert {p.kind.value: p.amount.cents for p in day3} == {
        "credit_memo": 312000,
        "correction": 312000,
    }
    credit = next(p for p in day3 if p.kind == "credit_memo")
    correction = next(p for p in day3 if p.kind == "correction")
    assert [a.line_id for a in credit.allocations] == ["D1"]
    assert credit.business_key.endswith(":credit_memo:D1:inc:1")
    assert correction.corrects_receipt_id == next(
        r.receipt_id for r in w.state.receipts if ":dispute:" in r.business_key
    )
    assert correction.business_key.endswith(f":correction:{correction.corrects_receipt_id}:1")
    for i, p in enumerate(day3, 3):
        w.record(p, i)
    assert w.ledger_balance(w.facts.case_id).cents == 132000
    assert derive(w, w.facts.case_id) == []
    assert call(w, "get_ledger").result["submitted_dispute_cents_by_line"] == {
        "D1": 0,
        "D2": 132000,
    }


def test_hero_approved_unsent_needs_no_correction():
    w = hero()
    w.record(next(p for p in derive(w, w.facts.case_id) if p.kind == "credit_memo"), 1)
    replace_basis(w, hero(after=True))
    derived = derive(w, w.facts.case_id)
    assert {p.kind.value for p in derived} == {"credit_memo", "dispute"}
    assert next(p for p in derived if p.kind == "dispute").amount.cents == 132000


def set_disputed(w, cents):
    line = w.state.decision.lines[0]
    line.valid = Money(cents=12000 - cents)
    line.disputed = Money(cents=cents)
    line.verdict = "partial" if cents < 12000 else "invalid"


def test_receipt_level_corrections_newest_first_and_sequences():
    w = hero()
    set_disputed(w, 10000)
    original = next(p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind == "dispute")
    w.record(original, 1)
    set_disputed(w, 12000)
    supplement = next(p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind == "dispute")
    assert supplement.amount.cents == 2000 and supplement.business_key.endswith(":inc:1")
    w.record(supplement, 2)
    set_disputed(w, 3000)
    corrections = [p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind == "correction"]
    assert [(p.corrects_receipt_id, p.amount.cents) for p in corrections] == [
        ("MOCK-2", 2000),
        ("MOCK-1", 7000),
    ]
    for n, p in enumerate(corrections, 3):
        w.record(p, n)
    set_disputed(w, 1000)
    correction = next(p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind == "correction")
    assert correction.amount.cents == 2000
    assert correction.business_key.endswith(":correction:MOCK-1:2")
    w.record(correction, 5)
    assert not [
        p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind in {"correction", "dispute"}
    ]
    set_disputed(w, 2000)
    increment = next(p for p in derive(w, w.facts.case_id, ["D1"]) if p.kind == "dispute")
    assert increment.amount.cents == 1000 and increment.business_key.endswith(":inc:2")


@pytest.mark.parametrize(
    "args,code",
    [
        ({"kind": "dispute"}, "line_id_required"),
        ({"kind": "notice", "line_id": "D1"}, "line_id_not_allowed"),
        ({"kind": "claim", "line_id": "D1"}, "line_id_not_allowed"),
        ({"kind": "dispute", "line_id": "unknown"}, "unknown_line"),
    ],
)
def test_readiness_argument_errors(args, code):
    result = call(hero(), "readiness", **args)
    assert not result.ok and result.issues[0].code == code


def test_per_line_readiness_does_not_block_other_line():
    w = hero()
    w.facts.facts = [f for f in w.facts.facts if f.evidence_id != "pod-v1"]
    w.decide()
    blocked = call(w, "readiness", kind="dispute", line_id="D1")
    ready = call(w, "readiness", kind="dispute", line_id="D2")
    assert blocked.ok and blocked.result["readiness"]["status"] == "not_ready"
    assert ready.ok and ready.result["readiness"]["status"] == "ready"
    result = call(
        w,
        "draft_proposal",
        kind="dispute",
        line_ids=["D2"],
        recipient="SYNTHETIC recipient",
        draft_text="SYNTHETIC MOCK LLM fake",
        citations=[],
    )
    assert result.ok and result.result["accepted"] and result.result["amount_cents"] == 132000


def test_static_output_claim_items_at_evaluation_clock():
    from .test_policy_readiness import inputs

    w = hero()
    facts, docs, revisions = inputs()
    facts.case_id = w.facts.case_id
    for doc in docs:
        doc.case_id = facts.case_id
    w.facts = facts
    w.inventory = docs
    w.revisions = revisions
    w.decide()
    result = static_output(w, w.facts.case_id)
    assert result.claim_items
    statuses = {i.item_id: i.status for i in result.claim_items}
    assert statuses["claim.notice_receipt"] == "missing"
    assert statuses["claim.doc.pod"] == "present"
    assert statuses["claim.doc.statement"] == "present"
    assert statuses["claim.waiting_period"] == "unknown"
    assert static_output(hero(), "SYNTHETIC-H").claim_items == []


def test_tool_decision_never_accepts_model_verdict_or_money():
    w = hero()
    before = w.state.decision
    result = call(
        w,
        "propose_decision",
        lines=[dict(line_id="D1", verdict="valid", citations=[], rationale="wrong")],
    )
    assert result.ok and not result.result["accepted"] and w.state.decision == before
    result = call(
        w,
        "propose_decision",
        lines=[
            dict(line_id="D1", verdict="invalid", citations=[], rationale="SYNTHETIC rationale")
        ],
    )
    assert result.ok and result.result["accepted"]
    assert w.state.decision.lines[0].disputed.cents == 312000
    result = call(
        w,
        "draft_proposal",
        kind="dispute",
        line_ids=["D1"],
        recipient="SYNTHETIC recipient",
        draft_text="SYNTHETIC MOCK",
        citations=[],
        amount_cents=1,
    )
    assert not result.ok and result.issues[0].code == "invalid_args"


def test_unknown_and_bench_tools_rejected_and_no_automatic_approval():
    w = hero()
    for name in ["unknown", "submit_approved", "wait_until"]:
        assert not call(w, name).ok
    p = proposal(w, "credit_memo", ["D2"])
    w.save_proposal(p)
    result = call(w, "request_approval", proposal_id=p.proposal_id, version=1)
    assert result.ok and result.result["queued"] and w.state.proposals[0].status == "proposed"
    assert not call(w, "request_approval", proposal_id="foreign", version=1).ok


def test_read_search_list_scope_and_limits():
    w = text_world()
    assert (
        call(w, "search_evidence", query="received 360").result["hits"][0]["evidence_id"]
        == "text-doc"
    )
    read = call(w, "read_evidence", evidence_id="text-doc", max_chars=10)
    assert read.ok and read.result["truncated"] and len(read.result["text"]) == 10
    assert (
        call(w, "read_evidence", evidence_id="invoice", locator="fields.total_cents").result["text"]
        == "4800000"
    )
    assert len(call(w, "list_evidence", kind="pod").result["rows"]) == 2
    assert not call(w, "search_evidence", query="", max_hits=0).ok
    assert not call(w, "read_evidence", evidence_id="text-doc", max_chars=-1).ok
    assert (
        call(w, "fetch_from_system", system="erp", query="SYNTHETIC missing").result["status"]
        == "not_found"
    )


@pytest.mark.parametrize("days,clamped,expected", [(0, True, 1), (100, True, 60), (14, False, 14)])
def test_schedule_and_end_gate(days, clamped, expected):
    w = hero()
    result = call(w, "schedule_followup", kind="follow_up", days_from_now=days)
    assert result.ok and result.result["clamped"] is clamped
    assert (w.state.due[0].due_at - w.clock.now()).days == expected
    result = call(w, "end", reason="done")
    assert result.ok and not result.result["accepted"] and len(result.result["unmet"]) == 2


def test_gate_target_recipient_hash_duplicates_and_amounts():
    w = hero()
    p = proposal(w, "credit_memo", ["D2"])
    changed = p.model_copy(
        update={"target": "mock_email", "recipient": "bad", "draft_sha256": "wrong"}
    )
    # Construct a typed invalid target rather than bypassing enum validation in the support.
    from recoup.contracts.models import Target

    changed.target = Target.mock_email
    assert {"wrong_target", "invalid_recipient", "draft_hash_mismatch"} <= codes(w, changed)
    changed = p.model_copy(update={"allocations": p.allocations * 2})
    assert {"duplicate_allocation", "amount_mismatch"} <= codes(w, changed)


def test_derivation_overcredit_and_stale_decision_fail_closed():
    w = hero()
    p = proposal(w, "credit_memo", ["D2"])
    w.record(p, 1)
    w.state.decision.lines[1].valid = Money(cents=1)
    with pytest.raises(GateError, match="over_credited"):
        derive(w, w.facts.case_id)
    w.state.decision.current = False
    with pytest.raises(GateError, match="stale_decision"):
        derive(w, w.facts.case_id)


def test_gate_independently_rejects_forged_decision_money():
    w = hero()
    w.state.decision.lines[1].valid = Money(cents=190000)
    p = proposal(w, "credit_memo", ["D2"])
    assert "decision_rule_mismatch" in codes(w, p)


def test_gate_resolves_rule_citations_even_when_draft_omits_them():
    w = hero()
    p = proposal(w, "credit_memo", ["D2"])
    w.evidence("contract").fields["promo.FALL26.cap_cents"] = 1
    assert "invalid_citation" in codes(w, p)


def test_quote_sign_does_not_fabricate_positive_money():
    w = text_world(text="SYNTHETIC price -$78.00", kind="invoice")
    result = call(w, "propose_fact", **fact_args(7800, "line.1.unit_price_cents", "price -$78.00"))
    assert not result.ok


def policy_world():
    from .test_policy_readiness import inputs

    w = hero()
    facts, docs, revisions = inputs(
        changes={"claim_doc.1": "invoice"}, remove=("claim_doc.2", "claim_doc.3")
    )
    policy_doc = next(doc for doc in docs if doc.kind == "insurance_policy")
    policy_doc.case_id = w.facts.case_id
    w.inventory.append(policy_doc)
    w.evidence("invoice").fields["buyer_id"] = "BUYER"
    w.facts.facts.extend(f for f in facts.facts if f.key == "buyer_id")
    w.facts.facts.extend(f for f in facts.facts if f.doc_kind == "insurance_policy")
    w.facts.docs.extend(d for d in facts.docs if d.kind == "insurance_policy")
    w.decide()
    return w


def test_notice_and_claim_gate_lifecycle_and_no_loss_amount():
    w = policy_world()
    s = session(w)
    a = dict(
        line_ids=[],
        recipient="SYNTHETIC recipient",
        draft_text="SYNTHETIC MOCK; does not establish coverage or eligibility.",
        citations=[],
    )
    rejected = s.call("draft_proposal", dict(kind="insurer_notice", **a))
    assert rejected.ok and not rejected.result["accepted"]
    assert "readiness_required" in {i["code"] for i in rejected.result["issues"]}
    assert s.call("readiness", {"kind": "notice"}).ok
    notice = s.call("draft_proposal", dict(kind="insurer_notice", **a))
    assert notice.ok and notice.result["accepted"]
    p = w.state.proposals[-1]
    assert p.amount is None and not p.allocations and p.balance_basis.cents == 624000
    assert "stale_balance" in codes(w, p.model_copy(update={"balance_basis": Money(cents=1)}))
    assert s.call("readiness", {"kind": "claim"}).ok
    claim = s.call("draft_proposal", dict(kind="claim_package", **a))
    assert claim.ok and claim.result["accepted"]
    p = w.state.proposals[-1]
    assert not codes(w, p, "save") and not codes(w, p, "approve")
    assert "claim_not_ready" in codes(w, p, "submit")


def test_exclusion_tool_preserves_distinct_answers():
    w = policy_world()
    facts, docs, _ = fact_inputs(
        [
            {
                "id": "policy-exclusions",
                "kind": "insurance_policy",
                "fields": {
                    "exclusion.1": "alpha",
                    "exclusion.2": "beta",
                    "clause.alpha": "SYNTHETIC clause A",
                    "clause.beta": "SYNTHETIC clause B",
                },
            }
        ],
        w.facts.case_id,
    )
    w.facts.facts.extend(facts.facts)
    w.facts.docs.extend(facts.docs)
    w.inventory.extend(docs)
    result = call(w, "check_policy", question="exclusions")
    assert result.ok
    answers = result.result["answers"]
    assert {a["clause_key"] for a in answers} == {"alpha", "beta"}
    assert len({a["clause_citation"]["locator"] for a in answers}) == 2


def test_missing_plan_and_product_end_after_proposals():
    w = hero()
    assert call(w, "plan_missing_evidence").result["items"] == []
    for p in derive(w, w.facts.case_id):
        w.save_proposal(p)
    assert call(w, "end", reason="SYNTHETIC done").result["accepted"]
    w.state.decision.lines.pop()
    assert not call(w, "end", reason="incomplete").result["accepted"]


@pytest.mark.parametrize(
    "text",
    [
        "Not only is coverage confirmed, payout is guaranteed.",
        "There is no delay: coverage is confirmed.",
        "Your claim is approved.",
    ],
)
def test_assertion_negation_scope_regressions(text):
    assert assertion_issues(text, [])


@pytest.mark.parametrize(
    "text",
    [
        "Please review coverage.",
        "We request a review of eligibility.",
        "Coverage is not established.",
    ],
)
def test_assertion_neutral_requests_and_post_target_negation(text):
    assert not assertion_issues(text, [])


def test_followup_completion_is_bound_to_latest_outbound_receipt():
    w = hero()
    for i, p in enumerate(derive(w, w.facts.case_id), 1):
        w.record(p, i)
    assert "follow-up schedule" in session(w).unmet()
    assert call(w, "schedule_followup", kind="follow_up", days_from_now=14).ok
    latest = next(r for r in w.state.receipts if ":dispute:" in r.business_key)
    assert w.state.due[-1].basis == latest.receipt_id
    assert "follow-up schedule" not in session(w).unmet()


def test_unconfirmed_money_cannot_enter_credit_gate():
    w = hero()
    p = proposal(w, "credit_memo", ["D2"])
    from recoup.contracts.models import FieldTrust

    fact = next(f for f in w.facts.facts if f.key == "promo.FALL26.cap_cents")
    fact.trust = FieldTrust.ocr
    p.citations = [fact.citation]
    assert {"untrusted_money", "decision_rule_mismatch"} <= codes(w, p)
