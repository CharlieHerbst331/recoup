"""Demo control flows through app-built, offline in-memory Worlds (design/02 §6)."""

from contextlib import contextmanager
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import recoup.app as app
from recoup.contracts.interfaces import TransientError
from recoup.ui.case import group_readiness

SCRIPT = Path(__file__).resolve().parents[2] / "recoup" / "ui" / "streamlit_app.py"


@pytest.fixture
def demo_page(monkeypatch):
    monkeypatch.setenv("RECOUP_LLM", "fake")
    real_build = app.build
    state = {"database": None, "calls": [], "closed": 0, "built": 0, "fail": {}}

    def build(config):
        service = real_build(config.model_copy(update={"db": ":memory:"}))
        state["built"] += 1
        if state["database"] is not None:
            service.world.db.deserialize(state["database"])
        for name in ("advance", "run"):
            operation = getattr(service, name)

            def track(*args, _name=name, _operation=operation, **kwargs):
                state["calls"].append((_name, args, kwargs))
                if _name in state["fail"]:
                    raise state["fail"][_name]
                return _operation(*args, **kwargs)

            monkeypatch.setattr(service, name, track)
        close = service.world.close

        def capture_and_close():
            state["database"] = service.world.db.serialize()
            state["day"] = service.world.clock.day()
            state["due"] = service.next_due_day()
            if service.world.list_cases():
                state["view"] = service.world.view("H")
                state["history"] = service.history("H")
            state["closed"] += 1
            close()

        monkeypatch.setattr(service.world, "close", capture_and_close)
        return service

    monkeypatch.setattr(app, "build", build)
    return AppTest.from_file(str(SCRIPT), default_timeout=30), state


def load_demo(page):
    page.run()
    page.sidebar.button(key="load_demo").click().run()
    assert not page.exception and not page.error


def key(proposal):
    return f"{proposal.case_id}:{proposal.proposal_id}:{proposal.version}"


def test_demo_edit_approve_submit_next_due_refreshes_proposals_and_readiness(demo_page):
    page, state = demo_page
    load_demo(page)
    assert set(page.dataframe[0].value["Case"]) == {"H", "C", "N"}
    page.selectbox(key="selected_case").select("H").run()
    proposal = next(row for row in state["view"].proposals if row.kind == "dispute")
    draft = proposal.draft_text + "\nPlease review the cited documents."
    page.text_area(key=f"draft:{key(proposal)}").set_value(draft)
    page.button(key=f"FormSubmitter:edit:{key(proposal)}-Edit").click().run()
    assert not page.exception and not page.error
    edited = next(row for row in state["view"].proposals if row.kind == "dispute")
    assert edited.version == proposal.version + 1 and edited.draft_text == draft
    page.button(key=f"approve:{key(edited)}").click().run()
    assert not page.exception and not page.error
    page.button(key=f"submit:{key(edited)}").click().run()
    assert not page.exception and not page.error
    receipt = state["history"].receipts[0]
    assert receipt.receipt_id.startswith("MOCK-")
    assert any(receipt.receipt_id in element.value for element in page.success)
    before = {row.proposal_id for row in state["view"].proposals}
    before_readiness = [row.model_dump_json() for row in state["view"].readiness]
    due = state["due"]
    assert due == 3
    assert f"Next due: day {due}" in [row.value for row in page.sidebar.caption]
    page.sidebar.button(key="advance_next_due").click().run()
    assert not page.exception and not page.error
    assert state["calls"][-1] == ("advance", (), {"to_next_due": True})
    assert state["day"] == due
    assert page.selectbox(key="selected_case").value == "H"
    assert any(f"DEMO CLOCK: day {due} " in row.value for row in page.info)
    correction = next(row for row in state["view"].proposals if row.kind == "correction")
    assert correction.proposal_id not in before
    assert correction.corrects_receipt_id == receipt.receipt_id
    assert f"Kind: correction · Target: {correction.target.value}" in [
        row.value for row in page.text
    ]
    texts = [row.value for row in page.text]
    for records in group_readiness(state["view"]).values():
        for record in records:
            assert f"{record.readiness_id} · {record.line_id or 'Case'} · {record.status}" in texts
    assert state["view"].readiness
    assert [row.model_dump_json() for row in state["view"].readiness] != before_readiness
    assert state["closed"] == state["built"]


def test_controls_disable_without_work_and_run_only_the_open_case(demo_page, monkeypatch):
    page, state = demo_page
    page.run()
    assert page.sidebar.button(key="run_agent").disabled
    assert page.sidebar.button(key="advance_next_due").disabled
    assert "Next due: none scheduled." in [row.value for row in page.sidebar.caption]
    load_demo(page)
    page.selectbox(key="selected_case").select("H").run()
    spinners = []

    @contextmanager
    def spinner(text):
        spinners.append(text)
        yield

    monkeypatch.setattr("streamlit.spinner", spinner)
    page.sidebar.button(key="run_agent").click().run()
    assert not page.exception and not page.error
    assert state["calls"] == [("run", ("H",), {})]
    assert spinners == ["Running agent for case H…"]
    assert page.title[0].value.startswith("Case H:")
    page.sidebar.number_input(key="advance_days").set_value(2)
    page.sidebar.button(key="advance_n_days").click().run()
    assert not page.exception and not page.error
    assert state["calls"][-1] == ("advance", (), {"days": 2})
    assert spinners[-1] == "Advancing 2 days…"
    assert state["day"] == 2
    assert any("DEMO CLOCK: day 2 " in row.value for row in page.info)
    assert state["closed"] == state["built"]


@pytest.mark.parametrize("control,operation", [("advance_n_days", "advance"), ("run_agent", "run")])
def test_control_errors_are_visible_and_world_is_closed(demo_page, control, operation):
    page, state = demo_page
    load_demo(page)
    page.selectbox(key="selected_case").select("H").run()
    state["fail"][operation] = TransientError("SYNTHETIC temporary failure")
    page.sidebar.button(key=control).click().run()
    assert not page.exception
    assert page.error[0].value == "Error: SYNTHETIC temporary failure"
    assert state["day"] == 0
    assert state["closed"] == state["built"]


def test_database_switch_clears_open_case(demo_page):
    page, _ = demo_page
    load_demo(page)
    page.selectbox(key="selected_case").select("H").run()
    page.sidebar.text_input(key="db_path").set_value("runs/other.db").run()
    assert not page.exception and not page.error
    assert page.selectbox(key="selected_case").value is None
    assert page.sidebar.button(key="run_agent").disabled
