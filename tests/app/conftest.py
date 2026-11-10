"""Offline owner-local test lane authorized by external r10 design/04 §3."""

import os
import socket

import pytest


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in app tests")

    for name in os.environ:
        if name.endswith("API_KEY"):
            monkeypatch.delenv(name)
    for name in (
        "RECOUP_DB",
        "RECOUP_LLM",
        "RECOUP_MODEL",
        "OPENAI_BASE_URL",
        "RECOUP_VISION",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
