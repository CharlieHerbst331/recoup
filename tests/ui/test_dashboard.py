"""Dashboard labels and filters display contract state (design/02 §6)."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.models import CaseStatus, ProposalStatus
from recoup.ui.dashboard import (
    approval_count,
    case_tags,
    dashboard_counts,
    demo_next_step,
    filter_cases,
    needs_attention,
)


@pytest.fixture(scope="module")
def dashboard_database():
    instance = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        root = Path(__file__).resolve().parents[2] / "cases/demo"
        instance.load([str(root / case_id) for case_id in ("H", "C", "N")])
        return instance.world.db.serialize()
    finally:
        instance.world.close()


@pytest.fixture
def dashboard_service(dashboard_database):
    instance = build(RecoupConfig(db=":memory:", llm="fake"))
    instance.world.db.deserialize(dashboard_database)
    try:
        yield instance
    finally:
        instance.world.close()


def test_current_proposals_drive_tags_and_case_counts(dashboard_service):
    instance = dashboard_service
    original = next(row for row in instance.world.view("H").proposals if row.kind == "dispute")
    instance.edit(
        original.proposal_id, original.version, draft_text="SYNTHETIC request for review."
    )
    case = instance.world.view("H")
    assert approval_count(case) == 3
    assert ("Needs approval · 3", "orange") in case_tags(case)
    assert dashboard_counts([case])["Need approval"] == 1
    edited = next(row for row in case.proposals if row.kind == "dispute")
    assert edited.version == 2
    instance.approve(edited.proposal_id, edited.version)
    approved = instance.world.view("H")
    assert approval_count(approved) == 2
    assert ("Approved · 1", "blue") in case_tags(approved)
    assert ("Checklist gaps", "gray") in case_tags(approved)
    assert all("ready to submit" not in label.lower() for label, _ in case_tags(approved))
    assert filter_cases([approved], "Approved", "") == [approved]
    assert demo_next_step([approved]).startswith("Submit H’s approved dispute")
    instance.submit(edited.proposal_id, edited.version)
    submitted = instance.world.view("H")
    assert ("MOCK submitted · 1", "green") in case_tags(submitted)
    assert filter_cases([submitted], "MOCK submitted", "") == [submitted]
    assert dashboard_counts([submitted])["MOCK submitted"] == 1
    assert not filter_cases([submitted], "Approved", "")
    assert demo_next_step([submitted]).startswith("Advance to next due")
    instance.advance(to_next_due=True)
    assert demo_next_step([instance.world.view("H")]).startswith("Review H’s new correction")


@pytest.mark.parametrize("status", ["stale", "cancelled", "rejected", "submitted_mock"])
def test_non_proposed_versions_do_not_count_as_approval_requests(dashboard_service, status):
    base = dashboard_service.world.view("C")
    case = base.model_copy(
        update={
            "proposals": [
                row.model_copy(update={"status": ProposalStatus(status)}) for row in base.proposals
            ]
        }
    )
    assert approval_count(case) == 0
    assert not filter_cases([case], "Needs approval", "")
    assert not filter_cases([case], "Approved", "")


def test_search_and_attention_filters_preserve_order_and_do_not_mutate(service):
    cases = service.world.list_cases()
    before = [case.model_dump_json() for case in cases]
    assert [case.case_id for case in filter_cases(cases, "All cases", "  shortage  ")] == ["H"]
    assert [case.case_id for case in filter_cases(cases, "All cases", "northWIND")] == ["H"]
    assert filter_cases(cases, "All cases", "missing customer") == []
    assert filter_cases([], "All cases", "") == []
    assert filter_cases(cases, "All cases", "") == cases
    for status, label in [
        (CaseStatus.needs_human, "Human review needed"),
        (CaseStatus.needs_info, "Needs information"),
    ]:
        case = cases[0].model_copy(update={"status": status, "readiness": []})
        assert needs_attention(case)
        assert any(tag == label for tag, _ in case_tags(case))
        assert filter_cases([case], "Needs attention", "") == [case]
    assert [case.model_dump_json() for case in cases] == before
    assert dashboard_counts([]) == {
        "Cases": 0,
        "Need approval": 0,
        "Approved cases": 0,
        "MOCK submitted": 0,
    }
    assert demo_next_step([]) == "Load the demo cases to start the walkthrough."
