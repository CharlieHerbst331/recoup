"""Selected-case execution through the real assembly and SQLite boundary (§4.5)."""

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import DueWork
from recoup.contracts.testing import NullController

from .test_build_integration import synthetic_bundle


def populated():
    service = build(RecoupConfig(db=":memory:"))
    for case_id in ("A", "B"):
        service.world.load_bundle(synthetic_bundle().model_copy(update={"case_id": case_id}))
    return service


def test_selected_case_leaves_other_case_and_pending_events_untouched():
    service = populated()
    try:
        work = service.world.schedule(
            DueWork(
                due_id="RECHECK-B",
                case_id="B",
                kind="recheck",
                due_at=service.world.clock.now(),
                basis=service.world.evidence_set_hash("B"),
                idempotency_key="RECHECK-B",
            )
        )
        pending = service.world.pending_events()
        before = service.world.history("B")
        assert service.run("A")[0].case_id == "A"
        assert service.world.current_decision("A") is not None
        assert service.world.history("B") == before
        assert work in service.world.due(service.world.clock.now())
        remaining = {e.event_id for e in service.world.pending_events()}
        assert {e.event_id for e in pending} <= remaining
        service.run()
        assert service.world.current_decision("B") is not None
        assert not service.world.pending_events()
    finally:
        service.world.close()


def test_selected_scope_rolls_back_and_restores_after_failure(monkeypatch):
    service = populated()
    try:
        before = service.world.history("A")
        engine = service._parts.engine
        original = engine.investigate

        def fail(world, case_id, llm, run_id):
            original(world, case_id, llm, run_id)
            raise RuntimeError("after investigation")

        monkeypatch.setattr(engine, "investigate", fail)
        with pytest.raises(RuntimeError, match="after investigation"):
            service.run("A")
        assert service.world.history("A") == before
        assert service.controller._case_ids is None
        monkeypatch.setattr(engine, "investigate", original)
        service.run()
        assert service.world.current_decision("B") is not None
    finally:
        service.world.close()


def test_custom_legacy_controller_fails_closed_for_selected_case():
    class Legacy:
        name = "legacy"

        def react(self, *args):
            raise AssertionError("Unscoped controller must not run")

    service = build(RecoupConfig(db=":memory:"), controller=Legacy())
    try:
        service.world.load_bundle(synthetic_bundle())
        with pytest.raises(GateError) as rejected:
            service.run("APP-G1")
        assert rejected.value.issues[0].code == "controller_scope_unsupported"
    finally:
        service.world.close()


def test_nested_scope_restores_and_does_not_delegate_events():
    service = populated()
    try:
        adapter = service.controller
        with adapter.scope(["A"]):
            with adapter.scope(["B"]):
                assert adapter._case_ids == ("B",)
            assert adapter._case_ids == ("A",)
            with pytest.raises(GateError):
                adapter.react(service.world, service.world.pending_events(), "TEST")
        assert adapter._case_ids is None
        for invalid in ([], ["A", "A"], [""]):
            with pytest.raises(ValueError):
                with adapter.scope(invalid):
                    pass
    finally:
        service.world.close()


def test_explicit_null_controller_stays_inert_for_selected_case():
    controller = NullController()
    service = build(RecoupConfig(db=":memory:"), controller=controller)
    try:
        service.world.load_bundle(synthetic_bundle())
        service.run("APP-G1")
        assert service.controller is controller
        assert service.world.current_decision("APP-G1") is None
    finally:
        service.world.close()
