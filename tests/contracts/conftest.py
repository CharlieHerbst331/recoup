import os
import socket

import pytest


@pytest.fixture(autouse=True)
def offline_without_api_keys(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in contract tests")

    for name in os.environ:
        if name.endswith("API_KEY"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("RECOUP_LLM", "fake")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
