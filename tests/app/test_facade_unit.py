"""Facade orchestration with owner-local spies; these are NOT G1 integration tests."""

import builtins
from datetime import timedelta

import pytest

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import DomainEvent
from recoup.contracts.testing import ScriptedLLM

from .doubles import (
    START,
    ControllerSpy,
    NullControllerSpy,
    WorldSpy,
    bundle,
    counted_parts,
    document,
)


@pytest.fixture
def service(monkeypatch):
    from recoup.app import Recoup, RecoupConfig
    from recoup.contracts import testing

    parts, llm = counted_parts(), ScriptedLLM(())

    def no_assembly(*args, **kwargs):
        raise AssertionError("Injected facade attempted default parts/controller/LLM construction")

    monkeypatch.setattr(testing, "stub_parts", no_assembly)
    monkeypatch.setattr(testing, "NullController", no_assembly)
    monkeypatch.setattr(testing, "ScriptedLLM", no_assembly)

    original_import = builtins.__import__

    def no_providers(name, *args, **kwargs):
        if name.startswith(("recoup.engine", "recoup.world")):
            raise AssertionError(f"Unit facade tried to import provider {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_providers)
    return Recoup(
        RecoupConfig(db=":memory:", run_id="UNIT-RUN"),
        WorldSpy(),
        ControllerSpy("scripted-T-min"),
        parts,
        llm,
    )


def write_bundle(path, case_id="SYNTHETIC-A"):
    path.mkdir(parents=True)
    (path / "bundle.json").write_text(bundle(case_id).model_dump_json())
    return path


@pytest.mark.parametrize("name", ["null", "scripted-T-min", "REF", "BAD"])
def test_public_mutations_dispatch_only_to_selected_controller(service, tmp_path, name):
    service.controller = NullControllerSpy() if name == "null" else ControllerSpy(name)
    directory = write_bundle(tmp_path / "case")
    doc = document()
    released = DomainEvent(
        event_id="RELEASED-ISOLATION",
        case_id="SYNTHETIC-A",
        seq=1,
        at=START + timedelta(days=2),
        type="evidence_added",
        ref="POD-V2",
    )
    service.world.day_events[2] = [released]
    actions = [
        lambda: service.load([str(directory)]),
        lambda: service.run("SYNTHETIC-A"),
        lambda: service.advance(),
        lambda: service.advance(),
        lambda: service.add_evidence("SYNTHETIC-A", doc, "synthetic-dir"),
        lambda: service.confirm_field("E-UNIT", "received"),
        lambda: service.edit("P-UNIT", 1, draft_text="SYNTHETIC edit", editor="reviewer"),
        lambda: service.approve("P-UNIT", 2, "reviewer"),
        lambda: service.reject("P-UNIT", 2, "Need POD", "reviewer"),
        lambda: service.submit("P-UNIT", 2),
    ]
    for number, action in enumerate(actions, 1):
        action()
        assert len(service.controller.calls) == number
        world, events, run_id, day, write_count = service.controller.calls[-1]
        assert world is service.world
        assert run_id == "UNIT-RUN"
        assert write_count == len(service.world.calls)
        if number in (2, 3):
            assert events == []
        elif number == 4:
            assert events == [released]
        else:
            assert events == service.world.pending_events()
    assert service.world.calls == [
        ("load_bundle", (bundle(), str(directory)), {}),
        ("advance_to", (1,), {}),
        ("advance_to", (2,), {}),
        ("add_evidence", ("SYNTHETIC-A", doc, "synthetic-dir"), {}),
        ("confirm_field", ("E-UNIT", "received", "user"), {}),
        ("edit_proposal", ("P-UNIT", 1), {"draft_text": "SYNTHETIC edit", "editor": "reviewer"}),
        ("approve", ("P-UNIT", 2, "reviewer"), {}),
        ("reject", ("P-UNIT", 2, "reviewer", "Need POD"), {}),
        ("submit", ("P-UNIT", 2), {}),
    ]
    assert service._parts.engine.calls == []
    with pytest.raises(StopIteration):
        service.llm.next("", [], [])


def test_clock_callbacks_interleave_each_day_even_without_events(service):
    event = DomainEvent(
        event_id="RELEASED",
        case_id="SYNTHETIC-A",
        seq=1,
        at=START + timedelta(days=2),
        type="evidence_added",
        ref="POD-V2",
    )
    service.world.day_events[2] = [event]
    assert service.advance(days=3) == ["SYNTHETIC-A", "SYNTHETIC-B"]
    assert [(call[1], call[3], call[4]) for call in service.controller.calls] == [
        ([], 1, 1),
        ([event], 2, 2),
        ([], 3, 3),
    ]
    assert service.world.clock.day() == 3


def test_mutation_return_records_are_not_replaced_by_controller_output(service):
    assert service.add_evidence("SYNTHETIC-A", document()) is service.world.evidence_row
    assert service.confirm_field("E-UNIT", "received") is service.world.fact
    assert service.edit("P-UNIT", 1) is service.world.proposal
    assert service.approve("P-UNIT", 2) is service.world.approval
    assert service.submit("P-UNIT", 2) is service.world.receipt
    assert service.reject("P-UNIT", 2, "Need POD").reason == "Need POD"
    assert service.world.calls[-1] == ("reject", ("P-UNIT", 2, "user", "Need POD"), {})


@pytest.mark.parametrize(
    "operation,invoke",
    [
        ("add_evidence", lambda r: r.add_evidence("SYNTHETIC-A", document())),
        ("confirm_field", lambda r: r.confirm_field("E-UNIT", "received")),
        ("edit_proposal", lambda r: r.edit("P-UNIT", 1)),
        ("approve", lambda r: r.approve("P-UNIT", 2)),
        ("reject", lambda r: r.reject("P-UNIT", 2, "Need POD")),
        ("submit", lambda r: r.submit("P-UNIT", 2)),
    ],
)
def test_world_gate_errors_propagate_without_controller_dispatch(service, operation, invoke):
    service.world.failure = operation
    with pytest.raises(GateError) as exc:
        invoke(service)
    assert [issue.code for issue in exc.value.issues] == ["unit_rejected"]
    assert service.controller.calls == []


def test_controller_failure_propagates_preserving_world_event(service):
    class BrokenController:
        name = "broken-unit"

        def react(self, world, events, run_id):
            raise RuntimeError("unit controller failed")

    service.controller = BrokenController()
    with pytest.raises(RuntimeError, match="unit controller failed"):
        service.submit("P-UNIT", 2)
    assert len(service.world.pending_events()) == 1


def test_duplicate_evidence_still_dispatches_once(service):
    service.world.duplicate = True
    assert service.add_evidence("SYNTHETIC-A", document()) is None
    assert len(service.controller.calls) == 1


def test_load_batch_validates_all_inputs_then_dispatches_once(service, tmp_path):
    parent = tmp_path / "cases"
    first = write_bundle(parent / "a")
    second = write_bundle(parent / "b", "SYNTHETIC-B")
    results = service.load([str(parent)])
    assert [result.case_id for result in results] == ["SYNTHETIC-A", "SYNTHETIC-B"]
    assert [call[1][1] for call in service.world.calls] == [str(first), str(second)]
    assert len(service.controller.calls) == 1
    assert len(service.controller.calls[0][1]) == 2


def test_invalid_later_bundle_does_not_partially_load(service, tmp_path):
    first = write_bundle(tmp_path / "a")
    second = tmp_path / "b"
    second.mkdir()
    (second / "bundle.json").write_text("{}")
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        service.load([str(first), str(second)])
    assert service.world.calls == []
    assert service.controller.calls == []


def test_load_requires_bundle_directories_and_handles_empty_list(service, tmp_path):
    assert service.load([]) == []
    with pytest.raises(FileNotFoundError, match="No bundle.json"):
        service.load([str(tmp_path)])
    with pytest.raises(NotADirectoryError):
        service.load([str(tmp_path / "missing")])
    assert service.controller.calls == []


def test_run_returns_views_after_callback_and_checks_unknown_case(service):
    class UpdatingController(ControllerSpy):
        def react(self, world, events, run_id):
            super().react(world, events, run_id)
            world.clock.current_day = 7

    service.controller = UpdatingController("unit-updater")
    assert [view.sim_day for view in service.run()] == [7, 7]
    views = service.run("SYNTHETIC-A")
    assert [view.case_id for view in views] == ["SYNTHETIC-A"]
    with pytest.raises(KeyError):
        service.run("unknown")
    assert len(service.controller.calls) == 2


@pytest.mark.parametrize("days", [-1, 1.5, True, "2"])
def test_invalid_clock_arguments_do_not_mutate(service, days):
    with pytest.raises(ValueError, match="nonnegative integer"):
        service.advance(days=days)
    assert service.world.calls == []
    assert service.controller.calls == []


def test_zero_days_and_conflicting_clock_arguments(service):
    assert service.advance(days=0) == []
    with pytest.raises(ValueError, match="not both"):
        service.advance(days=2, to_next_due=True)
    assert service.controller.calls == []


def test_next_due_injection_and_no_due_work(service):
    service._next_due_day = lambda: 2
    assert service.next_due_day() == 2
    service.advance(to_next_due=True)
    assert [call[3] for call in service.controller.calls] == [1, 2]
    service._next_due_day = lambda: None
    assert service.advance(to_next_due=True) == []
    assert len(service.controller.calls) == 2


def test_due_today_runs_callback_without_advancing_clock(service):
    service._next_due_day = lambda: 0
    service.advance(to_next_due=True)
    assert service.world.clock.day() == 0
    assert service.world.calls == []
    assert len(service.controller.calls) == 1


def test_unwired_due_lookup_and_regression_gate_are_explicit(service):
    with pytest.raises(NotImplementedError, match="006-2B"):
        service.advance(to_next_due=True)
    with pytest.raises(NotImplementedError, match="006-4"):
        service.check_regression()
    assert service.controller.calls == []


def test_read_exports_and_tool_sessions_use_injected_parts_without_reacting(service):
    assert service.history("SYNTHETIC-A") is service.world.case_history
    assert service.static_output("SYNTHETIC-A").case_id == "SYNTHETIC-A"
    assert service.rules_only("SYNTHETIC-B").case_id == "SYNTHETIC-B"
    assert service._parts.engine.calls == [
        ("static_output", service.world, "SYNTHETIC-A"),
        ("rules_only", service.world, "SYNTHETIC-B"),
    ]
    session = service.tool_session("SYNTHETIC-A", "TOOL-RUN", "REF")
    assert service._parts.tools.calls == [(service.world, "SYNTHETIC-A", "TOOL-RUN", "REF")]
    assert {schema["name"] for schema in session.schemas()} == {"list_evidence", "read_evidence"}
    assert service.controller.calls == []


def test_constructor_preserves_config_and_uses_supplied_ports():
    from recoup.app import Recoup, RecoupConfig

    config = RecoupConfig()
    world, controller, parts, llm = (
        WorldSpy(),
        ControllerSpy("REF"),
        counted_parts(),
        ScriptedLLM(()),
    )
    service = Recoup(config, world, controller, parts, llm, next_due_day=lambda: 3)
    assert config.run_id is None
    assert service.config.run_id
    assert service.world is world
    assert service.controller is controller
    assert service.llm is llm
    assert service.next_due_day() == 3
