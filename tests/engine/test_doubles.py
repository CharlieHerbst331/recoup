"""Checks of owned scripts, not World integration acceptance."""

import pytest

from recoup.contracts.interfaces import LLMResponse
from recoup.contracts.testing import ScriptedLLM

from .doubles import ScriptedClock, ScriptedWorld
from .fixtures import NOW, fact_inputs


def test_world_script_checks_arguments_order_and_consumption():
    facts, _, _ = fact_inputs([], "synthetic")
    clock = ScriptedClock(NOW, day=3)
    world = ScriptedWorld(
        clock, [("synthetic", None, facts), ("synthetic", facts.basis_hash, facts)]
    )
    assert world.fact_set("synthetic") == facts
    assert world.fact_set("synthetic", facts.basis_hash) == facts
    world.assert_finished()
    assert world.calls == [
        ("fact_set", "synthetic", None),
        ("fact_set", "synthetic", facts.basis_hash),
    ]
    assert world.clock.day() == 3
    assert (world.clock.now() - NOW).days == 3
    with pytest.raises(NotImplementedError):
        world.fact_set("synthetic")
    with pytest.raises(NotImplementedError, match="submit"):
        world.submit("P-1", 1)
    with pytest.raises(NotImplementedError, match="transaction"):
        world.transaction()


def test_wrong_arguments_and_unconsumed_script_fail():
    facts, _, _ = fact_inputs([], "synthetic")
    world = ScriptedWorld(ScriptedClock(NOW), [("synthetic", None, facts)])
    with pytest.raises(AssertionError, match="Unused"):
        world.assert_finished()
    with pytest.raises(AssertionError):
        world.fact_set("other-case")


def test_shared_scripted_llm_stays_offline_and_exhausts():
    response = LLMResponse(tool_calls=[], text="SYNTHETIC", model_id="script", mode="fake")
    llm = ScriptedLLM([response])
    assert llm.next("system", [], []) == response
    with pytest.raises(StopIteration):
        llm.next("system", [], [])
