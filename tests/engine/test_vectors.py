"""007-0 data acceptance only; these tests do not execute rules or intake."""

import json
import re

import pytest

from recoup.contracts.models import Basis, DeductionReason, FieldTrust, Verdict
from recoup.contracts.resolve import resolve_citation

from .fixtures import VECTOR_DIR, fact_inputs, line_input, load_vectors, rule_inputs

VECTORS = load_vectors()
RULE_VECTORS = load_vectors("run_rules")
BY_ID = {vector["id"]: vector for vector in VECTORS}


@pytest.mark.parametrize("path", sorted(VECTOR_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_vector_envelope_and_scalar_vocabulary(path):
    document = json.loads(path.read_text())
    assert document["provenance"] == "SYNTHETIC"
    assert document["fixture_format"] == "sonny-rule-vectors-v1"
    assert document["stage"] in {"run_rules", "deduction_intake"}
    for vector in document["vectors"]:
        assert "design/02" in vector["reference"]
        for doc in vector["input"]["documents"]:
            for key, value in doc["fields"].items():
                assert re.fullmatch(r"[a-z_]+(?:\.[a-zA-Z0-9_-]+)*", key), key
                assert value is None or type(value) in (str, int, bool)
                if key.endswith(("_cents", "_bp")):
                    assert type(value) is int, key


def test_unique_ids_and_reason_coverage():
    assert len(BY_ID) == len(VECTORS)
    assert {v["input"]["line"]["reason"] for v in RULE_VECTORS} == {
        reason.value for reason in DeductionReason
    }
    for reason in DeductionReason:
        assert any(
            v["input"]["line"]["reason"] == reason
            and v["expected_finding"].get("basis") == "missing_evidence"
            for v in RULE_VECTORS
        )


@pytest.mark.parametrize("vector", RULE_VECTORS, ids=lambda v: v["id"])
def test_rule_vector_contract_inputs_and_expected_money(vector):
    lines, facts, ledger = rule_inputs(vector)
    assert len(lines) == 1
    assert facts.case_id == vector["id"]
    assert facts.docs
    assert lines[0].source_evidence_id in {doc.evidence_id for doc in facts.docs}
    assert all(row.case_id == facts.case_id for row in ledger)
    expected = vector["expected_finding"]
    # design/02 §5.3 negative deduction escalates the case, not a RuleFinding.
    if lines[0].claimed.cents < 0:
        assert expected["verdict"] == "needs_human"
        assert expected["valid_cents"] is expected["disputed_cents"] is None
        return
    Verdict(expected["verdict"])
    Basis(expected["basis"])
    valid, disputed = expected["valid_cents"], expected["disputed_cents"]
    if expected["basis"] == "proven":
        assert type(valid) is type(disputed) is int
        assert 0 <= valid <= lines[0].claimed.cents
        assert valid + disputed == lines[0].claimed.cents
        assert expected["verdict"] == (
            "valid" if valid == lines[0].claimed.cents else "invalid" if valid == 0 else "partial"
        )
    else:
        assert valid is disputed is None


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["id"])
def test_every_effective_fact_citation_resolves(vector):
    facts, evidence, revisions = fact_inputs(vector["input"]["documents"], vector["id"])
    for fact in facts.facts:
        assert resolve_citation(fact.citation, facts, evidence, revisions) == fact.value
    assert {row.evidence_id for row in evidence} == {row.evidence_id for row in facts.docs}
    assert all(
        fact.evidence_id in {d.evidence_id for d in facts.docs if d.readable}
        for fact in facts.facts
    )


def test_critical_expectations_are_present():
    def expected(name):
        return BY_ID[name]["expected_finding"]

    assert expected("gross_basis_prior_credit")["valid_cents"] == 6000
    assert expected("gross_basis_prior_credit")["disputed_cents"] == 4000
    assert BY_ID["gross_basis_prior_credit"]["downstream_reference"]["new_credit_cents"] == 4000
    assert rule_inputs(BY_ID["gross_basis_prior_credit"])[2][0].amount.cents == 2000
    for name in ("amendment_same_date_conflict", "late_pod_tracking_conflict"):
        assert expected(name)["basis"] == "contradiction"
    for name in ("amendment_unauthorized_role", "amendment_missing_author"):
        assert "unauthorized_amendment" in expected(name)["flags_include"]
    for suffix, valid, disputed in (
        ("d1_before_pod_v2", 0, 312000),
        ("d1_after_pod_v2", 312000, 0),
        ("d2_before_pod_v2", 180000, 132000),
        ("d2_after_pod_v2", 180000, 132000),
    ):
        finding = expected(f"hero_{suffix}")
        assert (finding["valid_cents"], finding["disputed_cents"]) == (valid, disputed)
    for name, amounts in {
        "tolerance_claimed_100_entitled_98": (98, 2),
        "tolerance_claimed_100_entitled_99": (100, 0),
        "tolerance_claimed_100_entitled_100": (100, 0),
        "tolerance_claimed_100_entitled_101": (100, 0),
        "tolerance_claimed_1_entitled_0": (1, 0),
        "tolerance_claimed_2_entitled_0": (0, 2),
        "tolerance_claimed_0_entitled_0": (0, 0),
    }.items():
        assert (expected(name)["valid_cents"], expected(name)["disputed_cents"]) == amounts


def test_intake_expectations_are_typed_and_mutually_exclusive():
    for vector in load_vectors("deduction_intake"):
        lines = [line_input(row) for row in vector["expected_added_lines"]]
        assert not ({"U1", "NP"} <= {line.line_id for line in lines})
    assert BY_ID["zero_paid_with_deduction_is_u1"]["expected_added_lines"] == [
        {"line_id": "U1", "reason": "unexplained_short_pay", "claimed_cents": 6000}
    ]
    assert BY_ID["np_zero_paid_no_deductions"]["expected_added_lines"] == [
        {"line_id": "NP", "reason": "nonpayment", "claimed_cents": 10000}
    ]
    assert BY_ID["np_balance_owed"]["expected_route"] == "follow_up"
    assert BY_ID["u1_requests_reason"]["expected_finding"]["missing"] == ["reason"]


@pytest.mark.parametrize("method", ["ocr", "vision"])
def test_confirmed_money_is_revision_with_fact_locator(method):
    confirmed = BY_ID[f"pricing_confirmed_{method}"]
    facts, evidence, revisions = fact_inputs(confirmed["input"]["documents"], "trust")
    fact = next(f for f in facts.facts if f.key == "price.SKU-1_cents")
    assert fact.origin == "fact"
    assert fact.trust == FieldTrust.human_confirmed
    assert fact.citation.locator == f"fact:{fact.fact_id}"
    assert resolve_citation(fact.citation, facts, evidence, revisions) == 400
    unconfirmed = BY_ID[f"pricing_unconfirmed_{method}"]
    other, _, _ = fact_inputs(unconfirmed["input"]["documents"], "trust")
    assert other.basis_hash != facts.basis_hash
    assert next(f for f in other.facts if f.key == fact.key).trust == method


def test_factory_results_do_not_share_mutable_fields():
    vector = BY_ID["pricing_partial"]
    first, _, _ = fact_inputs(vector["input"]["documents"], "isolation")
    first.facts.clear()
    second, _, _ = fact_inputs(vector["input"]["documents"], "isolation")
    assert second.facts
    unreadable, _, _ = fact_inputs(
        [{"id": "rma", "kind": "return_auth", "readable": False, "fields": {"authorized_qty": 5}}],
        "unreadable",
    )
    assert not unreadable.facts
    assert not unreadable.docs[0].readable
