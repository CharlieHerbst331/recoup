"""Configuration and import-time independence; no provider integration here."""

import subprocess
import sys

import pytest
from pydantic import ValidationError


def test_defaults_are_offline_and_no_environment_is_cached(monkeypatch):
    from recoup.app import RecoupConfig

    assert RecoupConfig().model_dump() == {
        "db": "runs/recoup.db",
        "llm": "fake",
        "model": None,
        "base_url": None,
        "vision": False,
        "run_id": None,
    }
    assert RecoupConfig.from_env() == RecoupConfig()
    for name, value in {
        "RECOUP_DB": ":memory:",
        "RECOUP_LLM": "replay",
        "RECOUP_MODEL": "unit-model",
        "OPENAI_BASE_URL": "https://unused.example.test/v1",
        "RECOUP_VISION": "true",
    }.items():
        monkeypatch.setenv(name, value)
    assert RecoupConfig.from_env() == RecoupConfig(
        db=":memory:",
        llm="replay",
        model="unit-model",
        base_url="https://unused.example.test/v1",
        vision=True,
    )
    assert RecoupConfig().llm == "fake"
    monkeypatch.setenv("RECOUP_LLM", "fake")
    assert RecoupConfig.from_env().llm == "fake"


@pytest.mark.parametrize("value,expected", [("0", False), ("1", True), ("false", False)])
def test_vision_environment_boolean(monkeypatch, value, expected):
    from recoup.app import RecoupConfig

    monkeypatch.setenv("RECOUP_VISION", value)
    assert RecoupConfig.from_env().vision is expected


@pytest.mark.parametrize("name,value", [("RECOUP_LLM", "typo"), ("RECOUP_VISION", "maybe")])
def test_invalid_environment_fails_explicitly(monkeypatch, name, value):
    from recoup.app import RecoupConfig

    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        RecoupConfig.from_env()


def test_import_does_not_load_world_engine_or_llm_provider():
    script = """
import sys
import importlib.abc
class NoProviders(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('recoup.world', 'recoup.engine', 'openai')):
            raise AssertionError('Premature provider import: ' + fullname)
sys.meta_path.insert(0, NoProviders())
import recoup.app
assert recoup.app.RecoupConfig().llm == 'fake'
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_build_propagates_missing_provider_without_fallback(monkeypatch):
    import builtins

    from recoup.app import RecoupConfig, build
    from recoup.contracts.testing import NullController

    original_import = builtins.__import__
    missing = ModuleNotFoundError("Unit-injected missing SqliteWorld", name="recoup.world")

    def no_world(name, *args, **kwargs):
        if name == "recoup.world.store":
            raise missing
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_world)
    with pytest.raises(ModuleNotFoundError) as exc:
        build(RecoupConfig(db=":memory:"), controller=NullController())
    assert exc.value is missing
