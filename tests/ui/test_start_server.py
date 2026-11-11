"""Offline process lifecycle checks; no subprocesses, sockets or provider calls."""

import json
from types import SimpleNamespace

import pytest

from recoup.ui import start_server


@pytest.fixture
def startup(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setenv("RECOUP_ACCESS_SECRET", "synthetic-access-secret-at-least-32-characters")
    monkeypatch.setattr(start_server.time, "sleep", lambda _: None)
    calls = []

    def spawn(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=123, poll=lambda: None)

    monkeypatch.setattr(start_server.subprocess, "Popen", spawn)
    return tmp_path, calls


def test_repeated_launch_reuses_one_process_without_recording_credentials(startup, monkeypatch):
    data, calls = startup
    health = iter([False, True, True])
    monkeypatch.setattr(start_server, "healthy", lambda: next(health))
    start_server.ensure_server(data)
    start_server.ensure_server(data)
    assert len(calls) == 1
    assert calls[0][1]["cwd"] == data / "app"
    assert calls[0][1]["start_new_session"] is True
    state = (data / "server-state.json").read_text()
    assert "synthetic-key" not in state and "synthetic-access" not in state
    assert json.loads(state)["pid"] == 123


def test_failed_startup_is_bounded(startup, monkeypatch):
    data, calls = startup
    health_calls = []
    monkeypatch.setattr(start_server, "healthy", lambda: health_calls.append(1) or False)
    with pytest.raises(RuntimeError, match="startup unavailable"):
        start_server.ensure_server(data)
    assert len(calls) == 1
    assert len(health_calls) == 61


def test_secret_rotation_never_kills_an_unrelated_reused_pid(startup, monkeypatch):
    data, calls = startup
    (data / "server-state.json").write_text(json.dumps({"pid": 123, "config": "stale"}))
    monkeypatch.setattr(start_server, "healthy", lambda: True)
    monkeypatch.setattr(start_server.Path, "read_bytes", lambda _: b"unrelated-process")
    monkeypatch.setattr(start_server.os, "kill", lambda *_: pytest.fail("Killed unrelated process"))
    with pytest.raises(RuntimeError, match="does not match"):
        start_server.ensure_server(data)
    assert calls == []
