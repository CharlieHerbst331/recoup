"""Regressions for identity ownership and policy-reference intake."""

import pytest

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import Decision, Proposal, Readiness


def test_escaped_evidence_components_avoid_cross_case_identity_collisions(world, bundle):
    first = bundle.model_copy(deep=True)
    first.case_id = "A-B"
    first.docs = [
        BundleDoc(doc_ref="C", kind="invoice", title="Invoice", fields={"total_cents": 1000})
    ]
    second = first.model_copy(deep=True)
    second.case_id = "A"
    second.docs[0].doc_ref = "B-C"
    world.load_bundle(first)
    world.load_bundle(second)
    assert world.active_evidence("A-B")[0].evidence_id == "EV-A%2DB-C-v1"
    assert world.active_evidence("A")[0].evidence_id == "EV-A-B%2DC-v1"
    third = first.model_copy(update={"case_id": "A%2DB"})
    world.load_bundle(third)
    assert world.active_evidence("A%2DB")[0].evidence_id == "EV-A%252DB-C-v1"


def test_readiness_decision_and_proposal_ids_cannot_change_case_owner(world, bundle):
    world.load_bundle(bundle)
    world.load_bundle(bundle.model_copy(update={"case_id": "OTHER"}))
    basis = world.evidence_set_hash("CASE")
    other_basis = world.evidence_set_hash("OTHER")
    readiness = Readiness(
        readiness_id="R",
        case_id="CASE",
        kind="claim",
        status="not_ready",
        items=[],
        evidence_set_hash=basis,
    )
    world.save_readiness(readiness)
    with pytest.raises(GateError, match="identity_conflict"):
        world.save_readiness(
            readiness.model_copy(update={"case_id": "OTHER", "evidence_set_hash": other_basis})
        )
    assert world.readiness("CASE") == [readiness]
    assert world.readiness("OTHER") == []
    decision = Decision(
        decision_id="D",
        case_id="CASE",
        version=1,
        evidence_set_hash=basis,
        lines=[],
        current=True,
        model_id="test",
        llm_mode="fake",
        prompt_version="test",
        created_at=world.clock.now(),
    )
    world.save_decision(decision)
    with pytest.raises(GateError, match="identity_conflict"):
        world.save_decision(
            decision.model_copy(update={"case_id": "OTHER", "evidence_set_hash": other_basis})
        )
    assert world.current_decision("CASE").decision_id == "D"
    p = Proposal(
        proposal_id="P",
        business_key="CASE:info_request:U1",
        version=1,
        case_id="CASE",
        kind="info_request",
        target="mock_email",
        recipient="buyer@example.test",
        amount=None,
        draft_text="Please provide information.",
        draft_sha256="",
        citations=[],
        decision_id=None,
        decision_version=None,
        evidence_set_hash=basis,
        status="proposed",
        created_at=world.clock.now(),
        created_by="agent",
    )
    p = world.save_proposal(p)
    for key in (p.business_key, "OTHER:info_request:U1"):
        with pytest.raises(GateError, match="identity_conflict"):
            world.save_proposal(
                p.model_copy(
                    update={
                        "case_id": "OTHER",
                        "business_key": key,
                        "evidence_set_hash": other_basis,
                    }
                )
            )
    assert world.view("CASE").proposals == [p]
    assert world.view("OTHER").proposals == []


def test_reference_only_policy_loads_local_policy_and_embedded_does_not_duplicate(
    world, bundle, tmp_path
):
    directory = tmp_path / "cases" / "demo" / "CASE"
    directory.mkdir(parents=True)
    policies = tmp_path / "cases" / "policies"
    policies.mkdir()
    policy = BundleDoc(
        doc_ref="P-LOCAL",
        kind="insurance_policy",
        title="SYNTHETIC policy",
        fields={"policy_id": "P-LOCAL", "credit_limit_cents": 100000},
    )
    (policies / "P-LOCAL.json").write_text(policy.model_dump_json())
    bundle.policy_ref = "P-LOCAL"
    world.load_bundle(bundle, str(directory))
    assert [
        row.doc_ref for row in world.active_evidence("CASE") if row.kind == "insurance_policy"
    ] == ["P-LOCAL"]
    embedded = bundle.model_copy(deep=True)
    embedded.case_id = "EMBEDDED"
    embedded.docs.append(policy)
    world.load_bundle(embedded, str(directory))
    assert (
        len([row for row in world.active_evidence("EMBEDDED") if row.kind == "insurance_policy"])
        == 1
    )


@pytest.mark.parametrize(
    "reference,code", [("MISSING-TEST-POLICY", "missing_policy"), ("../P-A", "invalid_policy_ref")]
)
def test_missing_or_unsafe_policy_rolls_back_intake(world, bundle, tmp_path, reference, code):
    bundle.policy_ref = reference
    with pytest.raises(GateError, match=code):
        world.load_bundle(bundle, str(tmp_path))
    assert world.list_cases() == []
    for table in ("evidence", "ledger", "events", "traces", "meta"):
        assert world.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
