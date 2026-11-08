"""Factory selection with counted owner-local providers, not actual G3 proof."""

import sys
from types import ModuleType

import pytest

from recoup.contracts.testing import NullController, ScriptedLLM, stub_parts


@pytest.fixture
def factory(monkeypatch):
    import recoup.app as module

    calls = []
    parts = stub_parts()
    llm = ScriptedLLM(())
    controller = NullController()
    engine = ModuleType("recoup.engine")
    engine.__path__ = []
    factory = ModuleType("recoup.engine.factory")

    def build_engine(config):
        calls.append(("parts", config.llm))
        return parts

    def get_llm(config):
        calls.append(("llm", config.llm))
        return llm

    def harness_controller(selected_parts, selected_llm):
        assert selected_parts is parts
        assert selected_llm is llm
        calls.append(("harness",))
        return controller

    factory.build_engine = build_engine
    factory.get_llm = get_llm
    factory.harness_controller = harness_controller
    monkeypatch.setitem(sys.modules, "recoup.engine", engine)
    monkeypatch.setitem(sys.modules, "recoup.engine.factory", factory)
    monkeypatch.setattr(module, "find_spec", lambda name: object())
    return module, calls, parts, llm, controller


def test_default_factory_assembles_exactly_once(factory):
    module, calls, parts, llm, controller = factory
    service = module.build(module.RecoupConfig(db=":memory:", llm="replay"))
    assert calls == [("parts", "replay"), ("llm", "replay"), ("harness",)]
    assert service.controller is controller
    assert service.llm is llm
    assert service._parts is parts
    assert service.runtime_provider == "engine"
    assert service.world.list_cases() == []


@pytest.mark.parametrize("name", ["null", "scripted-T-min", "REF", "BAD"])
def test_custom_controller_does_not_construct_harness_or_harness_llm(factory, name):
    module, calls, parts, _, _ = factory
    controller = NullController()
    controller.name = name
    service = module.build(module.RecoupConfig(db=":memory:"), controller=controller)
    assert calls == [("parts", "fake")]
    assert service.controller is controller
    assert service._parts is parts
    assert service.world.attempt_controller == name
    with pytest.raises(StopIteration):
        service.llm.next("", [], [])


def test_installed_factory_import_error_propagates_without_stub_fallback(factory, monkeypatch):
    module, calls, *_ = factory
    monkeypatch.setitem(sys.modules, "recoup.engine.factory", None)
    with pytest.raises(ModuleNotFoundError):
        module.build(module.RecoupConfig(db=":memory:"))
    assert calls == []


def test_installed_factory_bug_propagates_without_creating_database(factory, monkeypatch, tmp_path):
    module, calls, *_ = factory

    def broken(config):
        raise RuntimeError("provider initialization failed")

    monkeypatch.setattr(sys.modules["recoup.engine.factory"], "build_engine", broken)
    path = tmp_path / "not-created.db"
    with pytest.raises(RuntimeError, match="provider initialization failed"):
        module.build(module.RecoupConfig(db=str(path)))
    assert not path.exists()
    assert calls == []


def test_missing_engine_fake_runtime_is_explicit(monkeypatch):
    import recoup.app as module

    monkeypatch.setattr(module, "find_spec", lambda name: None)
    service = module.build(module.RecoupConfig(db=":memory:"))
    assert service.runtime_provider == "contract-stubs"
    assert service.config.llm == "fake"
    with pytest.raises(NotImplementedError, match="Sonny"):
        module.build(module.RecoupConfig(db=":memory:", llm="live"))
