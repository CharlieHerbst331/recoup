"""Offline command tests; real persistence uses the app-built SQLite provider."""

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for key in os.environ:
        if key.endswith("API_KEY"):
            monkeypatch.delenv(key)
    for key in ("RECOUP_DB", "RECOUP_LLM", "RECOUP_MODEL", "RECOUP_VISION", "OPENAI_BASE_URL"):
        monkeypatch.delenv(key, raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("CLI tests must not use the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
