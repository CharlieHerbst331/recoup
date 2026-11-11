"""React adapter tests stay offline and use app-built memory Worlds (§6)."""

import json
from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.interfaces import GateError
from recoup.contracts.money import Money
from recoup.ui.api import case_data, dashboard_data, mutate, wire


@pytest.fixture(scope="module")
def database():
    service = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        root = Path(__file__).resolve().parents[2] / "cases/demo"
        service.load([str(root / case_id) for case_id in ("H", "C", "N")])
        return service.world.db.serialize()
    finally:
        service.world.close()


@pytest.fixture
def api_service(database):
    service = build(RecoupConfig(db=":memory:", llm="fake"))
    service.world.db.deserialize(database)
    try:
        yield service
    finally:
        service.world.close()


def test_react_dashboard_edit_approve_submit_and_day_three(api_service):
    service = api_service
    dashboard = dashboard_data(service)
    assert {case["case_id"] for case in dashboard["cases"]} == {"H", "C", "N"}
    assert dashboard["counts"]["Need approval"] == 3
    assert dashboard["clock"]["next_due_day"] == 3
    detail = case_data(service, "H")
    proposal = next(
        row["current"] for row in detail["proposals"] if row["current"]["kind"] == "dispute"
    )
    payload = {"proposal_id": proposal["proposal_id"], "version": proposal["version"]}
    with pytest.raises(GateError):
        mutate(service, "submit", payload)
    mutate(service, "edit", {**payload, "draft_text": proposal["draft_text"] + "\nPlease review."})
    payload["version"] += 1
    mutate(service, "approve", payload)
    assert dashboard_data(service)["counts"]["Approved cases"] == 1
    mutate(service, "submit", payload)
    after = case_data(service, "H")
    receipt = after["view"]["receipts"][0]
    assert receipt["receipt_id"].startswith("MOCK-")
    assert dashboard_data(service)["counts"]["MOCK submitted"] == 1
    mutate(service, "advance", {"to_next_due": True})
    assert dashboard_data(service)["clock"]["day"] == 3
    after = case_data(service, "H")
    assert any(row["current"]["kind"] == "correction" for row in after["proposals"])
    assert any(
        row["evidence"]["doc_ref"] == "POD" and row["evidence"]["version"] == 2
        for row in after["documents"]
    )
    assert after["view"]["readiness"]
    assert any(row["Type"] == "MOCK receipt" for row in after["timeline"])
    json.dumps(after)


def test_browser_wire_preserves_cents_and_large_evidence_integers():
    cents = 100000000000000001
    assert wire(Money(cents=cents)) == {"cents": str(cents), "currency": "USD"}
    assert wire({"qty": cents, "money": Money(cents=1), "version": 3}) == {
        "qty": str(cents),
        "money": {"cents": "1", "currency": "USD"},
        "version": 3,
    }


@pytest.mark.parametrize("cents", ["1.5", "1e3", "-1", 100, 1.5, ""])
def test_edit_rejects_non_integer_cents_before_mutating(api_service, cents):
    proposal = next(row for row in api_service.world.view("H").proposals if row.kind == "dispute")
    before = api_service.history("H").model_dump_json()
    with pytest.raises(ValueError, match="integer text"):
        mutate(
            api_service,
            "edit",
            {
                "proposal_id": proposal.proposal_id,
                "version": proposal.version,
                "allocations": [{"line_id": "D1", "cents": cents}],
            },
        )
    assert api_service.history("H").model_dump_json() == before


def test_exact_large_allocations_reach_service_gate(api_service):
    proposal = next(row for row in api_service.world.view("H").proposals if row.kind == "dispute")
    with pytest.raises(GateError) as exc:
        mutate(
            api_service,
            "edit",
            {
                "proposal_id": proposal.proposal_id,
                "version": proposal.version,
                "allocations": [{"line_id": "D1", "cents": "100000000000000001"}],
            },
        )
    assert any(issue.code == "allocation_increase" for issue in exc.value.issues)


def test_run_requires_open_case_and_reject_requires_reason(api_service):
    with pytest.raises(ValueError, match="Open a case"):
        mutate(api_service, "run", {})
    with pytest.raises(ValueError, match="nonnegative integer"):
        mutate(api_service, "advance", {"days": 1.5})
    proposal = api_service.world.view("H").proposals[0]
    with pytest.raises(ValueError, match="reason"):
        mutate(
            api_service,
            "reject",
            {"proposal_id": proposal.proposal_id, "version": proposal.version, "reason": " "},
        )
    assert api_service.world.clock.day() == 0


@pytest.fixture
def protocol_handler(database, monkeypatch):
    from types import SimpleNamespace

    import recoup.ui.server as host

    state = {"snapshots": {":memory:": database}, "built": 0, "closed": 0}

    def factory(config):
        instance = build(RecoupConfig(db=":memory:", llm="fake"))
        if config.db in state["snapshots"]:
            instance.world.db.deserialize(state["snapshots"][config.db])
        instance.config = instance.config.model_copy(update={"db": config.db})
        close = instance.world.close
        state["built"] += 1

        def capture_and_close():
            state["snapshots"][config.db] = instance.world.db.serialize()
            state["closed"] += 1
            close()

        monkeypatch.setattr(instance.world, "close", capture_and_close)
        return instance

    monkeypatch.setattr(host, "build", factory)
    handler = object.__new__(host.UIHandler)
    handler.server = SimpleNamespace(config=RecoupConfig(db=":memory:", llm="fake"))

    def response(data, status=200):
        state["data"], state["status"] = data, status

    handler._json = response
    return handler, state


def test_http_dispatch_closes_world_and_preserves_prior_simulation(protocol_handler):
    handler, state = protocol_handler
    original = handler.server.config
    handler._api("/api/advance", {"days": 2})
    assert state["status"] == 200
    assert state["data"]["dashboard"]["clock"]["day"] == 2
    handler._api("/api/fresh", {})
    assert state["status"] == 200
    assert handler.server.config.db != original.db
    assert state["data"]["dashboard"]["clock"]["day"] == 0
    assert len(state["data"]["dashboard"]["cases"]) == 3
    handler.server.config = original
    handler._api("/api/dashboard")
    assert state["data"]["clock"]["day"] == 2
    assert state["closed"] == state["built"] == 3


def test_http_service_gate_is_structured_and_connection_is_closed(protocol_handler):
    handler, state = protocol_handler
    handler._api("/api/cases/H")
    proposal = state["data"]["proposals"][0]["current"]
    handler._api(
        "/api/submit", {"proposal_id": proposal["proposal_id"], "version": proposal["version"]}
    )
    assert state["status"] == 409
    assert state["data"]["issues"]
    assert state["built"] == state["closed"]


def test_http_mutations_require_local_json_without_using_network(protocol_handler):
    from email.message import Message
    from io import BytesIO

    handler, state = protocol_handler
    handler.path = "/api/load"
    handler.headers = Message()
    handler.headers["Origin"] = "https://unrelated.example"
    handler.do_POST()
    assert state["status"] == 403
    del handler.headers["Origin"]
    handler.headers["Content-Type"] = "text/plain"
    handler.do_POST()
    assert state["status"] == 415
    handler.headers.replace_header("Content-Type", "application/json")
    handler.headers["Content-Length"] = "3"
    handler.rfile = BytesIO(b"bad")
    handler.do_POST()
    assert state["status"] == 400
    assert state["built"] == 0


def test_static_host_does_not_serve_files_outside_frontend(protocol_handler):
    handler, state = protocol_handler
    handler.path = "/%2e%2e/%2e%2e/AGENTS.md"
    handler.send_error = lambda status: state.update(status=status)
    handler.do_GET()
    assert state["status"] == 404
    assert state["built"] == 0


@pytest.mark.parametrize("path", ["/_stcore/health", "/assets/no-longer-present.js"])
def test_retired_or_missing_paths_are_not_replaced_with_frontend_html(protocol_handler, path):
    handler, state = protocol_handler
    handler.path = path
    handler.send_error = lambda status: state.update(status=status)
    handler.do_GET()
    assert state["status"] == 404
    assert state["built"] == 0
