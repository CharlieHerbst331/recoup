"""Exercise reruns and cleanup against app-built SQLite Worlds."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import recoup.app as app
from recoup.ui.case import money_table, timeline_rows

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "recoup" / "ui" / "streamlit_app.py"


@pytest.fixture(scope="module")
def loaded_h_database():
    # Navigation tests exercise rendering/reruns, not agent fixture construction
    # inside Streamlit's script deadline. Demo loading is tested separately below.
    service = app.build(app.RecoupConfig(db=":memory:", llm="fake"))
    try:
        service.load([str(ROOT / "cases" / "demo" / "H")])
        return service.world.db.serialize()
    finally:
        service.world.close()


@pytest.fixture
def tracked_app(monkeypatch):
    monkeypatch.setenv("RECOUP_LLM", "fake")
    monkeypatch.setenv("RECOUP_DB", "ignored-env.db")
    real_build = app.build
    configs, services, closed = [], [], []

    def build(config):
        configs.append(config)
        service = real_build(config.model_copy(update={"db": ":memory:"}))
        services.append(service)
        close = service.world.close

        def record_close():
            closed.append(service)
            close()

        monkeypatch.setattr(service.world, "close", record_close)
        return service

    monkeypatch.setattr(app, "build", build)
    return AppTest.from_file(str(SCRIPT), default_timeout=20), configs, services, closed


def test_empty_queue_banners_db_override_and_service_per_rerun(tracked_app):
    page, configs, services, closed = tracked_app
    page.run()
    assert not page.exception
    assert configs[0].db == "runs/demo.db"
    assert configs[0].llm == "fake"
    assert [element.value for element in page.info] == [
        "No cases loaded. Load demo cases in the Simulation lab or start a fresh simulation above.",
    ]
    banner = " ".join(item.proto.body for item in page.get("html"))
    for label in (
        "DEMO CLOCK: day 0 (2026-10-20, simulated)",
        "LLM: fake",
        "SYNTHETIC DATA",
        "MOCK actions",
        "MOCK ACKNOWLEDGMENT — not sent to any real system",
    ):
        assert label in banner
    assert closed == services
    page.sidebar.text_input(key="db_path").set_value("runs/other.db").run()
    assert not page.exception
    assert configs[1].db == "runs/other.db"
    assert len(services) == 2
    assert services[0] is not services[1]
    assert closed == services


def test_demo_load_button_displays_cases_and_closes_world(tracked_app):
    page, _, services, closed = tracked_app
    page.run()
    page.sidebar.button(key="load_demo").click().run()
    assert not page.exception
    assert not page.error
    assert len(page.dataframe) == 1
    rows = page.dataframe[0].value
    assert set(rows["Case"]) == {"H", "C", "N"}
    assert "Open balance (USD)" in rows
    assert {element.value for element in page.sidebar.info} == {
        "H: loaded",
        "C: loaded",
        "N: loaded",
    }
    assert len(services) == 2
    assert closed == services


def test_render_failure_still_closes_world(tracked_app, monkeypatch):
    page, _, services, closed = tracked_app
    tracked_build = app.build

    def build(config):
        service = tracked_build(config)

        def fail():
            raise ValueError("SYNTHETIC queue read failed")

        monkeypatch.setattr(service.world, "list_cases", fail)
        return service

    monkeypatch.setattr(app, "build", build)
    page.run()
    assert not page.exception
    assert page.error[0].value == "Error: SYNTHETIC queue read failed"
    assert len(services) == 1
    assert closed == services


def test_quarantine_has_its_own_table(tracked_app, loaded_h_database, monkeypatch):
    page, _, services, closed = tracked_app
    tracked_build = app.build

    def build(config):
        service = tracked_build(config)
        service.world.db.deserialize(loaded_h_database)
        service.load([str(ROOT / "cases" / "regression" / "r08")])
        return service

    monkeypatch.setattr(app, "build", build)
    page.run()
    assert not page.exception
    assert not page.error
    assert len(page.dataframe) == 2
    queue = page.dataframe[0].value
    quarantined = page.dataframe[1].value
    assert list(queue["Case"]) == ["H"]
    assert len(quarantined) == 1
    assert "EUR" in quarantined.iloc[0]["Reason"]
    assert list(quarantined.columns) == ["Case", "Reason", "Quarantined at"]
    assert closed == services


def test_pick_case_opens_details_and_back_returns_to_queue(
    tracked_app, loaded_h_database, monkeypatch
):
    page, _, services, closed = tracked_app
    tracked_build = app.build
    histories, views = [], []

    def build(config):
        service = tracked_build(config)
        service.world.db.deserialize(loaded_h_database)
        real_history = service.history

        def history(case_id):
            result = real_history(case_id)
            histories.append(result)
            views.append(service.world.view(case_id))
            return result

        monkeypatch.setattr(service, "history", history)
        return service

    monkeypatch.setattr(app, "build", build)
    page.run()
    assert page.title[0].value == "Case dashboard"
    page.radio(key="selected_case").set_value("H").run()
    assert not page.exception
    assert not page.error
    assert page.title[0].value == "Northwind Grocers"
    assert histories[-1].case_id == "H"
    assert any(table.value.to_dict("records") == money_table(views[-1]) for table in page.dataframe)
    assert page.dataframe[-1].value.to_dict("records") == timeline_rows(histories[-1])
    assert f"Status: {views[-1].status.value}" in [item.value for item in page.text]
    assert f"Insurance: {views[-1].insurance.value}" in [item.value for item in page.text]
    assert f"Latest update: {views[-1].status_reason}" in [item.value for item in page.text]
    assert [
        item.label for item in page.expander if item.label in {"Dispute", "Notice", "Claim"}
    ] == [
        "Dispute",
        "Notice",
        "Claim",
    ]
    for line in views[-1].decision.lines:
        assert f"Basis: {line.basis.value}" in [item.value for item in page.text]
        assert any(
            table.value.to_dict("records") == [citation.model_dump() for citation in line.citations]
            for table in page.dataframe
        )
    assert any("SYNTHETIC DATA" in item.proto.body for item in page.get("html"))
    assert closed == services
    page.sidebar.button(key="dashboard_home").click().run()
    assert not page.exception
    assert page.title[0].value == "Case dashboard"
    assert page.radio(key="selected_case").value is None
    assert closed == services
