"""007-1 pure acceptance against shared models; design/02 §3.7, §5.3."""

import json
import os
import subprocess
import sys
from copy import deepcopy

import pytest

from recoup.contracts.models import DocStatus, ExtractFailure
from recoup.contracts.resolve import resolve_citation
from recoup.engine.rules import (
    NeedsHumanError,
    proposal_kind,
    require_legal_authority,
    run_rules,
)
from tests.engine.fixtures import fact_inputs, load_vectors, rule_inputs

VECTORS = load_vectors("run_rules")


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_every_rule_vector(vector):
    lines, facts, ledger = rule_inputs(vector)
    before = deepcopy((lines, facts, ledger))
    expected = vector["expected_finding"]
    if expected["verdict"] == "needs_human":
        with pytest.raises(NeedsHumanError, match=expected["note_contains"]):
            run_rules(lines, facts, ledger)
        return
    (finding,) = run_rules(lines, facts, ledger)
    assert (lines, facts, ledger) == before
    assert finding.verdict == expected["verdict"]
    assert finding.basis == expected["basis"]
    assert all(c in [f.citation for f in facts.facts] for c in finding.citations)
    for name in ("valid", "disputed"):
        money = getattr(finding, name)
        assert (money.cents if money else None) == expected[name + "_cents"]
    assert set(expected.get("flags_include", [])) <= set(finding.flags)
    assert set(expected.get("cite_documents_include", [])) <= {
        c.evidence_id for c in finding.citations
    }
    if "missing" in expected:
        assert finding.missing == expected["missing"]
    if finding.basis == "proven":
        assert 0 <= finding.valid.cents <= lines[0].claimed.cents
        assert finding.valid.cents + finding.disputed.cents == lines[0].claimed.cents
        assert finding.verdict != "invalid" or finding.disputed.cents > 0
        assert finding.verdict != "valid" or finding.disputed.cents == 0
    else:
        assert finding.valid is finding.disputed is None
    if "expected_route" in vector:
        route = proposal_kind(lines[0], finding)
        assert (route.value if route else "none") == vector["expected_route"]
    if finding.basis == "contradiction":
        assert finding.contradictions
        assert all(a != b for a, b in finding.contradictions)


def vector_named(name):
    return deepcopy(next(v for v in VECTORS if v["id"] == name))


@pytest.mark.parametrize("trust", ["ocr", "vision"])
def test_confirmed_fact_only_money_and_citation(trust):
    vector = vector_named("pricing_confirmed_" + trust)
    lines, facts, ledger = rule_inputs(vector)
    money_fact = next(f for f in facts.facts if f.key == "price.SKU-1_cents")
    assert money_fact.origin == "fact"
    assert money_fact.citation.locator.startswith("fact:")
    (finding,) = run_rules(lines, facts, ledger)
    assert money_fact.citation in finding.citations
    documents = vector["input"]["documents"]
    current, evidence, revisions = fact_inputs(documents, facts.case_id)
    assert resolve_citation(money_fact.citation, current, evidence, revisions) == 400


@pytest.mark.parametrize("status", ["absent", "unreadable", "readable"])
def test_legal_authority_inventory(status):
    _, facts, _ = rule_inputs(vector_named("pricing_partial"))
    if status != "absent":
        facts.docs.append(
            DocStatus(
                evidence_id="legal",
                doc_ref="legal",
                kind="legal_authority",
                readable=status == "readable",
                failure=ExtractFailure.empty_text if status == "unreadable" else None,
            )
        )
    if status == "readable":
        assert require_legal_authority(facts) is None
    else:
        with pytest.raises(
            NeedsHumanError, match=("unreadable" if status == "unreadable" else "not supplied")
        ):
            require_legal_authority(facts)


def test_prior_credits_never_reduce_gross_rule_amounts():
    lines, facts, ledger = rule_inputs(vector_named("gross_basis_prior_credit"))
    (with_credit,) = run_rules(lines, facts, ledger)
    (without_credit,) = run_rules(lines, facts, [])
    assert with_credit.valid == without_credit.valid
    assert with_credit.disputed == without_credit.disputed
    assert with_credit.valid.cents == 6000
    assert "already_credited" in with_credit.flags


def test_duplicate_and_math_flags():
    lines, facts, ledger = rule_inputs(vector_named("pricing_partial"))
    lines[0].buyer_ref = "SYNTHETIC-REF"
    other = lines[0].model_copy(update={"line_id": "D2"})
    from recoup.contracts.models import LedgerEntry
    from recoup.contracts.money import Money
    from tests.engine.fixtures import NOW

    ledger.append(
        LedgerEntry(
            entry_id="invoice",
            case_id=facts.case_id,
            kind="invoice",
            amount=Money(cents=100000),
            line_id=None,
            source="SYNTHETIC",
            at=NOW,
        )
    )
    findings = run_rules([*lines, other], facts, ledger)
    assert all("duplicate_deduction_ref" in f.flags for f in findings)
    assert all("remittance_math_mismatch" in f.flags for f in findings)


def test_case_identity_does_not_affect_rules():
    lines, facts, ledger = rule_inputs(vector_named("hero_d1_after_pod_v2"))
    original = run_rules(lines, facts, ledger)
    facts.case_id = "unrelated"
    assert run_rules(lines, facts, ledger) == original


def test_zero_claim_needs_no_facts():
    lines, facts, ledger = rule_inputs(vector_named("tolerance_claimed_0_entitled_0"))
    facts.facts = []
    facts.docs = []
    (finding,) = run_rules(lines, facts, ledger)
    assert finding.verdict == "valid"
    assert finding.valid.cents == finding.disputed.cents == 0
    assert proposal_kind(lines[0], finding) is None


def test_u1_sku_does_not_require_invoice_to_request_reason():
    lines, facts, ledger = rule_inputs(vector_named("u1_requests_reason"))
    lines[0].sku = "UNKNOWN"
    facts.facts = []
    (finding,) = run_rules(lines, facts, ledger)
    assert finding.missing == ["reason"]


def test_claim_exceeds_line_total_flag():
    lines, facts, ledger = rule_inputs(vector_named("pricing_partial"))
    lines[0].claimed = lines[0].claimed.model_copy(update={"cents": 10001})
    (finding,) = run_rules(lines, facts, ledger)
    assert "claimed_exceeds_line_total" in finding.flags


def test_authorized_email_amendment_and_order_independence():
    vector = vector_named("amendment_latest_effective")
    vector["input"]["documents"][-1]["kind"] = "email"
    lines, facts, ledger = rule_inputs(vector)
    original = run_rules(lines, facts, ledger)
    facts.facts.reverse()
    assert run_rules(lines, facts, ledger) == original
    assert original[0].valid.cents == 2000


def test_nonpayment_with_classified_buyer_dispute_requires_info():
    vector = vector_named("np_balance_owed")
    vector["input"]["documents"].append(
        {
            "id": "buyer-dispute",
            "kind": "email",
            "fields": {"from": "buyer.invalid", "ded.1.line_id": "D1", "ded.1.reason": "shortage"},
        }
    )
    lines, facts, ledger = rule_inputs(vector)
    facts.buyer_senders = ["buyer.invalid"]
    (finding,) = run_rules(lines, facts, ledger)
    assert finding.verdict == "needs_info"
    assert proposal_kind(lines[0], finding) == "info_request"


@pytest.mark.parametrize(
    "vector",
    [v for v in VECTORS if v["expected_finding"]["verdict"] != "needs_human"],
    ids=lambda v: v["id"],
)
def test_rule_output_is_sorted_and_repeatable(vector):
    lines, facts, ledger = rule_inputs(vector)
    # Include proven zero claims and unresolved findings alongside the vector result.
    lines = (
        [
            lines[0].model_copy(
                update={
                    "line_id": "Z-zero",
                    "claimed": lines[0].claimed.model_copy(update={"cents": 0}),
                }
            )
        ]
        + lines
        + [lines[0].model_copy(update={"line_id": "A-missing", "reason": None})]
    )
    first = run_rules(lines, facts, ledger)
    second = run_rules(lines, facts, ledger)
    assert first == second
    assert (
        json.dumps([f.model_dump(mode="json") for f in first]).encode()
        == json.dumps([f.model_dump(mode="json") for f in second]).encode()
    )
    assert [f.line_id for f in first] == sorted(f.line_id for f in first)
    for finding in first:
        citations = [(c.evidence_id, c.locator, c.quote) for c in finding.citations]
        assert citations == sorted(citations)
        contradictions = [
            tuple((c.evidence_id, c.locator, c.quote) for c in pair)
            for pair in finding.contradictions
        ]
        assert all(pair == tuple(sorted(pair)) for pair in contradictions)
        assert contradictions == sorted(contradictions)
        assert finding.missing == sorted(finding.missing)
        assert finding.flags == sorted(finding.flags)
    facts.facts.reverse()
    assert run_rules(list(reversed(lines)), facts, ledger) == first


@pytest.mark.parametrize("vector_id", ["amendment_authorized", "amendment_same_date_conflict"])
def test_amendment_output_is_identical_across_hash_seeds(vector_id):
    vector = vector_named(vector_id)
    for document in vector["input"]["documents"]:
        if document["kind"] == "amendment":
            document["fields"]["price.SKU-2_cents"] = document["fields"]["price.SKU-1_cents"]
            document["fields"]["early_pay_bp"] = document["fields"]["price.SKU-1_cents"]
    script = """
import json
import sys
from recoup.engine.rules import run_rules
from tests.engine.fixtures import rule_inputs
findings = run_rules(*rule_inputs(json.load(sys.stdin)))
print(json.dumps([finding.model_dump(mode="json") for finding in findings]))
"""
    outputs = [
        subprocess.run(
            [sys.executable, "-c", script],
            input=json.dumps(vector),
            text=True,
            capture_output=True,
            check=True,
            env={**os.environ, "PYTHONHASHSEED": str(seed), "RECOUP_LLM": "fake"},
        ).stdout
        for seed in (1, 2)
    ]
    assert outputs[0].encode() == outputs[1].encode()
