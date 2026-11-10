"""Action cards exercise the facade with offline app-built Worlds (design/02 §6)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import recoup.app as app
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.models import GateIssue, ProposalStatus
from recoup.contracts.testing import NullController
from recoup.ui.actions import draft_diff, proposal_groups


@pytest.fixture(scope="module")
def proposal_database():
    service = app.build(app.RecoupConfig(db=":memory:", llm="fake"))
    try:
        service.load([str(Path(__file__).resolve().parents[2] / "cases" / "demo" / "H")])
        return service.world.db.serialize()
    finally:
        service.world.close()


@pytest.fixture
def action_service(proposal_database):
    service = app.build(app.RecoupConfig(db=":memory:", llm="fake"), controller=NullController())
    service.world.db.deserialize(proposal_database)
    try:
        yield service
    finally:
        service.world.close()


def dispute(service):
    return next(row for row in service.world.view("H").proposals if row.kind == "dispute")


def widget_key(proposal):
    return f"{proposal.case_id}:{proposal.proposal_id}:{proposal.version}"


def case_script():
    import recoup.app as app
    from recoup.ui.case_page import render_case

    service = app.build()
    try:
        render_case(service.world.view("H"), service.history("H"), service)
    finally:
        service.world.close()


@pytest.fixture
def action_page(action_service, monkeypatch):
    state = {"database": action_service.world.db.serialize(), "calls": [], "fail": {}}
    real_build = app.build

    def build():
        instance = real_build(
            app.RecoupConfig(db=":memory:", llm="fake"), controller=NullController()
        )
        instance.world.db.deserialize(state["database"])
        close = instance.world.close

        def track(name):
            operation = getattr(instance, name)

            def call(*args, **kwargs):
                state["calls"].append((name, args, kwargs))
                if name in state["fail"]:
                    raise state["fail"][name]
                return operation(*args, **kwargs)

            monkeypatch.setattr(instance, name, call)

        for name in ("edit", "approve", "reject", "submit"):
            track(name)

        def capture_and_close():
            state["history"] = instance.history("H")
            state["view"] = instance.world.view("H")
            state["database"] = instance.world.db.serialize()
            close()

        monkeypatch.setattr(instance.world, "close", capture_and_close)
        return instance

    monkeypatch.setattr(app, "build", build)
    return AppTest.from_function(case_script, default_timeout=20), state


def seed_page(action_page, service):
    page, state = action_page
    state["database"] = service.world.db.serialize()
    page.run()
    assert not page.exception
    return page, state


def edit_button(page, proposal):
    return page.button(key=f"FormSubmitter:edit:{widget_key(proposal)}-Edit")


def reject_button(page, proposal):
    return page.button(key=f"FormSubmitter:reject:{widget_key(proposal)}-Reject")


def test_group_versions_by_business_key_merge_history_and_prefer_view(action_service):
    original = dispute(action_service)
    edited = action_service.edit(
        original.proposal_id, original.version, draft_text="SYNTHETIC edit."
    )
    case, history = action_service.world.view("H"), action_service.history("H")
    # Exercise an older view and a duplicate history snapshot with a different status.
    case = case.model_copy(update={"proposals": [original]})
    history = history.model_copy(
        update={
            "proposals_all": [
                edited,
                original.model_copy(update={"status": ProposalStatus.stale}),
            ]
        }
    )
    before = case.model_dump_json(), history.model_dump_json()
    groups = proposal_groups(case, history)
    assert list(groups) == [original.business_key]
    assert groups[original.business_key] == [original, edited]
    assert groups[original.business_key][-1].version == 2
    assert (case.model_dump_json(), history.model_dump_json()) == before
    assert (
        proposal_groups(
            case.model_copy(update={"proposals": []}),
            history.model_copy(update={"proposals_all": []}),
        )
        == {}
    )
    changed_id = edited.model_copy(update={"proposal_id": "another-id"})
    assert proposal_groups(case, history.model_copy(update={"proposals_all": [changed_id]}))[
        original.business_key
    ] == [original, changed_id]


def test_action_cards_show_details_citations_history_and_diff(action_page, action_service):
    original = dispute(action_service)
    edited = action_service.world.save_proposal(
        original.model_copy(
            update={
                "draft_text": "SYNTHETIC revised request.\nPlease review.",
                "citations": action_service.world.view("H").decision.lines[0].citations,
            }
        )
    )
    page, state = seed_page(action_page, action_service)
    texts = [element.value for element in page.text]
    assert texts.count(original.business_key) == 1
    assert "Current version: v2 · Status: proposed" in texts
    assert f"Kind: {edited.kind.value} · Target: {edited.target.value}" in texts
    assert f"Recipient: {edited.recipient}" in texts
    assert "Amount (USD): $4,440.00" in texts
    assert original.draft_text in texts and edited.draft_text in texts
    assert any(
        table.value.to_dict("records") == [row.model_dump() for row in edited.citations]
        for table in page.dataframe
    )
    assert any(
        table.value.to_dict("records")
        == [
            {"Line": row.line_id, "Allocation (cents)": str(row.amount.cents)}
            for row in edited.allocations
        ]
        for table in page.dataframe
    )
    assert draft_diff(original, edited) in [code.value for code in page.code]
    assert "--- v1" in draft_diff(original, edited)
    assert "+SYNTHETIC revised request." in draft_diff(original, edited)
    assert not state["calls"] and not state["history"].approvals
    assert len([item for item in page.expander if item.label == "Version history"]) == 3
    assert widget_key(original) not in [button.key for button in page.button]


def test_edit_calls_facade_with_exact_version_and_integer_allocations(action_page, action_service):
    proposal = dispute(action_service)
    page, state = seed_page(action_page, action_service)
    key = widget_key(proposal)
    page.text_area(key=f"draft:{key}").set_value("SYNTHETIC request for review.")
    page.text_input(key=f"recipient:{key}").set_value(proposal.recipient)
    for index, allocation in enumerate(proposal.allocations):
        page.text_input(key=f"allocation:{key}:{allocation.line_id}").set_value(str(10001 + index))
    edit_button(page, proposal).click().run()
    assert not page.exception and not page.error
    name, args, changes = state["calls"][0]
    assert name == "edit" and args == (proposal.proposal_id, proposal.version)
    assert changes["recipient"] == proposal.recipient
    assert changes["draft_text"] == "SYNTHETIC request for review."
    assert [row.amount.cents for row in changes["allocations"]] == [10001, 10002]
    assert all(type(row.amount.cents) is int for row in changes["allocations"])
    current = next(
        row for row in state["view"].proposals if row.business_key == proposal.business_key
    )
    assert current.version == 2 and current.status == ProposalStatus.proposed
    assert not state["history"].approvals and not state["history"].receipts
    assert page.button(key=f"submit:{widget_key(current)}").disabled
    assert len([item for item in page.expander if item.label == "Version history"]) == 3


@pytest.mark.parametrize("value", ["1.5", "1e3", "-1", "", "NaN"])
def test_edit_rejects_non_integer_cents_without_mutation(action_page, action_service, value):
    proposal = dispute(action_service)
    page, state = seed_page(action_page, action_service)
    key = widget_key(proposal)
    page.text_input(key=f"allocation:{key}:{proposal.allocations[0].line_id}").set_value(value)
    edit_button(page, proposal).click().run()
    assert not page.exception
    assert "non-negative integer number of cents" in page.error[0].value
    assert not state["calls"]
    assert len(state["history"].proposals_all) == 3


def test_recipient_edits_surface_service_gate_inline(action_page, action_service):
    proposal = dispute(action_service)
    page, state = seed_page(action_page, action_service)
    page.text_input(key=f"recipient:{widget_key(proposal)}").set_value("unlisted@example.invalid")
    edit_button(page, proposal).click().run()
    assert not page.exception
    assert "recipient_not_allowed: unlisted@example.invalid" in [row.value for row in page.error]
    assert state["calls"][0][2]["recipient"] == "unlisted@example.invalid"
    assert not state["history"].approvals


def test_approval_and_submission_are_separate_and_receipt_survives_rerun(
    action_page, action_service
):
    proposal = dispute(action_service)
    page, state = seed_page(action_page, action_service)
    key = widget_key(proposal)
    assert page.button(key=f"submit:{key}").disabled
    page.button(key=f"approve:{key}").click().run()
    assert not page.exception and not page.error
    assert state["calls"] == [("approve", (proposal.proposal_id, proposal.version), {})]
    assert len(state["history"].approvals) == 1
    assert not state["history"].receipts
    assert not page.button(key=f"submit:{key}").disabled
    assert page.button(key=f"approve:{key}").disabled
    assert edit_button(page, proposal).disabled
    page.button(key=f"submit:{key}").click().run()
    assert not page.exception and not page.error
    assert state["calls"][-1] == ("submit", (proposal.proposal_id, proposal.version), {})
    receipt = state["history"].receipts[0]
    assert receipt.receipt_id.startswith("MOCK-")
    assert f"{receipt.receipt_id} · {receipt.label}" in [row.value for row in page.success]
    assert page.button(key=f"submit:{key}").disabled
    page.run()
    assert f"{receipt.receipt_id} · {receipt.label}" in [row.value for row in page.success]
    assert len(state["history"].receipts) == 1


@pytest.mark.parametrize("approved", [False, True])
def test_reject_requires_reason_and_calls_exact_version(action_page, action_service, approved):
    proposal = dispute(action_service)
    if approved:
        action_service.approve(proposal.proposal_id, proposal.version)
    page, state = seed_page(action_page, action_service)
    reject_button(page, proposal).click().run()
    assert not page.exception
    assert page.error[0].value == "Rejection reason is required."
    assert not state["calls"]
    page.text_input(key=f"reason:{widget_key(proposal)}").set_value("SYNTHETIC missing document")
    reject_button(page, proposal).click().run()
    assert not page.exception and not page.error
    assert state["calls"] == [
        (
            "reject",
            (proposal.proposal_id, proposal.version),
            {"reason": "SYNTHETIC missing document"},
        )
    ]
    assert state["history"].approvals[-1].reason == "SYNTHETIC missing document"
    assert not state["history"].approvals[-1].approved
    assert page.button(key=f"submit:{widget_key(proposal)}").disabled


@pytest.mark.parametrize("status", list(ProposalStatus))
def test_only_latest_approved_card_can_submit(action_page, action_service, status):
    original = dispute(action_service)
    action_service.approve(original.proposal_id, original.version)
    # An older approved snapshot must never get its own controls, even when the
    # latest snapshot is stale/cancelled. Store snapshots only to set up the UI.
    current = original.model_copy(update={"version": 2, "status": status})
    action_service.world._write_proposal(current)
    page, state = seed_page(action_page, action_service)
    buttons = [button for button in page.button if str(button.key).startswith("submit:")]
    assert f"submit:{widget_key(original)}" not in [button.key for button in buttons]
    assert page.button(key=f"submit:{widget_key(current)}").disabled == (
        status != ProposalStatus.approved
    )
    assert not state["calls"]


@pytest.mark.parametrize("operation", ["edit", "approve", "reject", "submit"])
def test_all_action_gate_issues_stay_on_card(action_page, action_service, operation):
    proposal = dispute(action_service)
    if operation == "submit":
        action_service.approve(proposal.proposal_id, proposal.version)
    page, state = seed_page(action_page, action_service)
    state["fail"][operation] = GateError(
        [
            GateIssue(code="stale_basis", message="SYNTHETIC basis changed", line_id="D1"),
            GateIssue(code="another_issue", message="SYNTHETIC issue"),
        ]
    )
    key = widget_key(proposal)
    if operation == "edit":
        button = edit_button(page, proposal)
    elif operation == "reject":
        page.text_input(key=f"reason:{key}").set_value("SYNTHETIC reason")
        button = reject_button(page, proposal)
    else:
        button = page.button(key=f"{operation}:{key}")
    button.click().run()
    assert not page.exception
    assert [row.value for row in page.error] == [
        "stale_basis [D1]: SYNTHETIC basis changed",
        "another_issue: SYNTHETIC issue",
    ]
    assert len(state["calls"]) == 1 and state["calls"][0][0] == operation
    # The error stays inside the same bordered card as its action controls.
    card = next(
        block
        for block in page.get("flex_container")
        if any(row.value == proposal.business_key for row in block.get("text"))
    )
    assert any(row.value == "another_issue: SYNTHETIC issue" for row in card.get("error"))
    assert not state["history"].receipts


def test_transient_submit_failure_is_inline_and_retry_remains_available(
    action_page, action_service
):
    proposal = dispute(action_service)
    action_service.approve(proposal.proposal_id, proposal.version)
    page, state = seed_page(action_page, action_service)
    state["fail"]["submit"] = TransientError("MOCK target temporarily unavailable")
    page.button(key=f"submit:{widget_key(proposal)}").click().run()
    assert not page.exception
    assert page.error[0].value == "MOCK target temporarily unavailable"
    assert not page.button(key=f"submit:{widget_key(proposal)}").disabled
    assert not state["history"].receipts


def test_large_cents_reach_service_exactly_and_limits_remain_service_owned(
    action_page, action_service
):
    proposal = dispute(action_service)
    page, state = seed_page(action_page, action_service)
    key = widget_key(proposal)
    page.text_input(key=f"allocation:{key}:{proposal.allocations[0].line_id}").set_value(
        "100000000000000001"
    )
    edit_button(page, proposal).click().run()
    assert not page.exception
    assert state["calls"][0][2]["allocations"][0].amount.cents == 100000000000000001
    assert "allocation_increase: Edits may only decrease existing line amounts" in [
        row.value for row in page.error
    ]
    assert not state["history"].approvals and not state["history"].receipts


def test_nonmonetary_action_edits_and_unchanged_draft_history(action_page, action_service):
    proposal = next(
        row for row in action_service.world.view("H").proposals if row.kind == "insurer_notice"
    )
    # A new version may change fields without changing draft text.
    current = proposal.model_copy(update={"version": 2})
    action_service.world._write_proposal(current)
    page, state = seed_page(action_page, action_service)
    assert "Amount (USD): None" in [row.value for row in page.text]
    assert "Draft text unchanged from previous version." in [row.value for row in page.caption]
    page.text_area(key=f"draft:{widget_key(current)}").set_value("SYNTHETIC request for review.")
    edit_button(page, current).click().run()
    assert not page.exception and not page.error
    assert state["calls"][0][2]["allocations"] == []
    assert not state["history"].approvals


def test_draft_diff_includes_final_newline_changes(action_service):
    original = dispute(action_service).model_copy(update={"draft_text": "SYNTHETIC draft."})
    edited = original.model_copy(update={"version": 2, "draft_text": "SYNTHETIC draft.\n"})
    diff = draft_diff(original, edited)
    assert "-SYNTHETIC draft." in diff and "+SYNTHETIC draft." in diff
    assert "\\ No newline at end of file" in diff
    assert draft_diff(original, original) == ""
