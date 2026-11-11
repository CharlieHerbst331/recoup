"""Offline browser/server boundary checks through app.build; design/02 §4.5, §6."""

import json
import logging
from pathlib import Path

import httpx2 as httpx
import openai
import pytest
from streamlit.testing.v1 import AppTest

from recoup.app import build
from recoup.contracts.bundle import CaseBundle
from recoup.ui import workbench as ui

ROOT = Path(__file__).resolve().parents[2]
ACCESS = "test-only-access-secret-32-characters-long"
API_KEY = "test-only-provider-key-never-render-this"


@pytest.fixture
def browser(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Network forbidden in workbench tests")

    monkeypatch.setattr("socket.socket.connect", no_network)
    monkeypatch.setattr("socket.create_connection", no_network)
    monkeypatch.setenv("RECOUP_ACCESS_SECRET", ACCESS)
    monkeypatch.setenv("OPENAI_API_KEY", API_KEY)
    monkeypatch.setenv("RECOUP_LLM", "fake")
    monkeypatch.delenv("RECOUP_VISION", raising=False)
    ui.access_gate.clear()
    # Restore global logging configuration after entry-point suppression.
    loggers = [
        logging.getLogger(name) for name in ("openai", "httpx", "httpcore", "httpx2", "httpcore2")
    ]
    saved = [(logger.handlers[:], logger.propagate) for logger in loggers]
    app = AppTest.from_string("from recoup.ui.workbench import main\nmain()")
    yield app
    for logger, (handlers, propagate) in zip(loggers, saved):
        logger.handlers, logger.propagate = handlers, propagate
    ui.access_gate.clear()


def button(app, label):
    return next(item for item in app.button if item.label == label)


def login(app, secret=ACCESS):
    app.run()
    app.text_input[0].set_value(secret)
    button(app, "Sign in").click().run()
    assert not app.exception


def memory_builder(monkeypatch, configs, *, persist=False):
    snapshot = None

    def factory(config):
        nonlocal snapshot
        configs.append(config)
        service = build(config.model_copy(update={"db": ":memory:"}))
        directory = ROOT / "cases/demo/H"
        bundle = CaseBundle.model_validate_json((directory / "bundle.json").read_text())
        service.world.load_bundle(bundle, str(directory))
        if persist:
            if snapshot is not None:
                service.world.db.deserialize(snapshot)
            close = service.world.close

            def save_and_close():
                nonlocal snapshot
                snapshot = service.world.db.serialize()
                close()

            service.world.close = save_and_close
        return service

    monkeypatch.setattr(ui, "build", factory)


@pytest.mark.parametrize("secret", [None, "short", API_KEY])
def test_missing_or_invalid_access_configuration_never_builds(browser, monkeypatch, secret):
    if secret is None:
        monkeypatch.delenv("RECOUP_ACCESS_SECRET")
    else:
        monkeypatch.setenv("RECOUP_ACCESS_SECRET", secret)
    monkeypatch.setattr(ui, "build", lambda *_: pytest.fail("Unauthenticated build"))
    browser.run()
    assert len(browser.error) == 1
    assert not browser.text_input
    assert not browser.exception


def test_bad_login_and_throttle_survive_new_sessions(browser, monkeypatch):
    monkeypatch.setattr(ui, "build", lambda *_: pytest.fail("Unauthenticated build"))
    login(browser, "wrong")
    assert browser.session_state["access_secret"] == ""
    assert "access" not in browser.session_state
    # A fresh browser cannot bypass the process-wide cooldown, even with the right secret.
    other = AppTest.from_string("from recoup.ui.workbench import main\nmain()")
    login(other)
    assert "access" not in other.session_state


def test_fake_agent_approval_and_mock_submission(browser, monkeypatch):
    configs = []
    memory_builder(monkeypatch, configs, persist=True)
    login(browser)
    assert configs[-1].llm == "fake"
    button(browser, "Run agent").click().run()
    assert not browser.exception
    view = json.loads(browser.json[0].value)
    assert view["decision"] is not None
    assert view["receipts"] == []
    assert all(item.disabled for item in browser.button if item.label == "Submit MOCK action")
    assert any(not item.disabled for item in browser.button if item.label == "Approve this version")
    assert any("LLM: fake" in item.value for item in browser.caption)
    button(browser, "Approve this version").click().run(timeout=30)
    assert not browser.error and not browser.exception
    submit = next(
        item for item in browser.button if item.label == "Submit MOCK action" and not item.disabled
    )
    submit.click().run(timeout=30)
    assert not browser.error and not browser.exception
    view = json.loads(browser.json[0].value)
    assert len(view["receipts"]) == 1
    assert view["receipts"][0]["receipt_id"].startswith("MOCK-")


def test_rotation_expiry_and_logout_block_build(browser, monkeypatch):
    configs = []
    memory_builder(monkeypatch, configs)
    login(browser)
    count = len(configs)
    monkeypatch.setenv("RECOUP_ACCESS_SECRET", ACCESS + "rotated")
    browser.run()
    assert len(configs) == count
    assert not any(item.label == "Run agent" for item in browser.button)
    login(browser, ACCESS + "rotated")
    digest, _ = browser.session_state["access"]
    browser.session_state["access"] = (digest, -8 * 60 * 60)
    count = len(configs)
    browser.run()
    assert len(configs) == count
    login(browser, ACCESS + "rotated")
    count = len(configs)
    button(browser, "Sign out").click().run()
    assert len(configs) == count
    assert "access" not in browser.session_state


def test_live_route_records_and_replays_without_network(browser, monkeypatch, tmp_path, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("RECOUP_LLM", "live")
    monkeypatch.setenv("RECOUP_MODEL", "claude-haiku-5-5")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.anthropic.com/v1/")
    monkeypatch.setenv("OPENAI_LOG", "debug")
    requests = []

    def respond(request):
        requests.append(request)
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        payload = json.loads(request.content)
        assert payload["model"] == "claude-haiku-5-5"
        assert "tools" in payload
        return httpx.Response(
            200,
            json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "claude-haiku-5-5",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "offline-end",
                                    "type": "function",
                                    "function": {"name": "end", "arguments": "{}"},
                                }
                            ],
                        },
                    }
                ],
            },
        )

    sdk = openai.OpenAI
    clients = []

    def client(**kwargs):
        result = sdk(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        clients.append(result)
        return result

    monkeypatch.setattr(openai, "OpenAI", client)
    configs = []
    memory_builder(monkeypatch, configs)
    try:
        browser.run()
        assert not requests and not configs
        login(browser)
        assert not requests  # Reading the queue does not run the agent.
        with caplog.at_level(logging.DEBUG):
            button(browser, "Run agent").click().run()
        assert not browser.exception
        assert requests
        assert all(
            str(request.url) == "https://api.anthropic.com/v1/chat/completions"
            for request in requests
        )
        recordings = list((tmp_path / "runs/recordings").glob("*.json"))
        assert recordings
        visible = str(browser) + caplog.text + "".join(path.read_text() for path in recordings)
        assert API_KEY not in visible and ACCESS not in visible
        assert any("LLM: live" in item.value for item in browser.caption)
        count = len(requests)
        monkeypatch.setenv("RECOUP_LLM", "replay")
        button(browser, "Run agent").click().run()
        assert not browser.exception
        assert len(requests) == count
        assert any("LLM: replay" in item.value for item in browser.caption)
    finally:
        for instance in clients:
            instance.close()


def test_sensitive_startup_error_is_not_rendered_or_logged(browser, monkeypatch, caplog):
    def fail(_):
        raise ValueError(f"sensitive configuration {API_KEY}")

    monkeypatch.setattr(ui, "build", fail)
    login(browser)
    assert len(browser.error) == 1
    assert API_KEY not in str(browser) + caplog.text
    assert not browser.exception


def test_demo_button_loads_paid_and_flagged_cases_through_app(browser, monkeypatch):
    configs = []
    memory_builder(monkeypatch, configs, persist=True)
    login(browser)
    button(browser, "Load SYNTHETIC demo cases (runs agent)").click().run(timeout=30)
    assert not browser.error and not browser.exception
    selector = next(item for item in browser.selectbox if item.label == "Case")
    assert set(selector.options) == {"H", "C", "N", "PAID-FULL", "PAID-INSTALLMENTS"}
    for case_id in ("PAID-FULL", "PAID-INSTALLMENTS"):
        selector.set_value(case_id).run()
        assert not browser.error and not browser.exception
        view = json.loads(browser.json[0].value)
        assert view["open_balance"]["cents"] == 0
        assert view["lines"] == view["decision"]["lines"] == []
        assert view["proposals"] == view["receipts"] == []
