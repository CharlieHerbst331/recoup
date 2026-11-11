"""SYNTHETIC queued-event regressions; design/02 §4.5, §5.2, §5.7–5.9."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import LLMResponse
from recoup.contracts.testing import NullController, ScriptedLLM
from recoup.engine.config import HarnessConfig
from recoup.engine.harness import HarnessEngine
from recoup.engine.llm import FakeLLM
from recoup.engine.llm.replay import ReplayLLM


@pytest.fixture
def world(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden in scheduler regressions")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)
    service = build(RecoupConfig(db=":memory:", llm="fake"), controller=NullController())
    try:
        yield service.world
    finally:
        service.world.close()


def load(world, case_id="H"):
    bundle = CaseBundle.model_validate_json(Path(f"cases/demo/{case_id}/bundle.json").read_text())
    assert world.load_bundle(bundle).status == "loaded"
    return case_id


class CountInvestigations(FakeLLM):
    def __init__(self, limit=None):
        self.starts = 0
        self.limit = limit

    def next(self, system, messages, tools):
        if len(messages) == 1:
            self.starts += 1
            if self.limit is not None:
                assert self.starts <= self.limit, "Redundant model investigation"
        return super().next(system, messages, tools)


@pytest.mark.parametrize("case_id", ["H", "C", "N"])
def test_loaded_demo_events_share_one_accepted_investigation(world, case_id):
    load(world, case_id)
    events = world.pending_events()
    assert len(events) > 2
    llm = CountInvestigations(limit=1)
    engine = HarnessEngine()
    assert engine.handle(world, llm, "SYNTHETIC-drain") == [case_id]
    assert llm.starts == 1
    assert not world.pending_events()
    view = world.view(case_id)
    assert view.status != "needs_human", view.status_reason
    assert not engine._unmet(world, case_id)
    assert view.decision and view.proposals and not view.receipts
    assert not world.history(case_id).approvals
    traces = world.history(case_id).traces
    acknowledgments = [t for t in traces if t.kind == "event"]
    assert [t.result["event_id"] for t in acknowledgments] == [e.event_id for e in events]
    assert "investigation_reused_from" not in acknowledgments[0].result
    assert all(
        t.result["investigation_reused_from"] == events[0].event_id for t in acknowledgments[1:]
    )
    assert sum(t.tool == "end" for t in traces) == 1
    # Neither an empty drain nor a subsequent explicit investigation reuses the cache.
    assert engine.handle(world, llm, "SYNTHETIC-empty") == []
    llm.limit = 2
    engine.investigate(world, case_id, llm, "SYNTHETIC-explicit")
    assert llm.starts == 2


def test_new_evidence_during_drain_requires_fresh_investigation(world, monkeypatch):
    cid = load(world)
    original = world.mark_event
    injected = False

    def acknowledge(event_id):
        nonlocal injected
        original(event_id)
        if not injected:
            injected = True
            world.add_evidence(
                cid,
                BundleDoc(
                    doc_ref="POD",
                    version=2,
                    kind="pod",
                    title="SYNTHETIC revised POD",
                    fields={"signed": True, "received.SKU-1": 360},
                ),
            )

    monkeypatch.setattr(world, "mark_event", acknowledge)
    llm = CountInvestigations(limit=2)
    HarnessEngine().handle(world, llm, "SYNTHETIC-changing-basis")
    assert llm.starts == 2
    view = world.view(cid)
    assert view.decision.evidence_set_hash == world.evidence_set_hash(cid)
    assert next(d for d in view.decision.lines if d.line_id == "D1").verdict == "valid"
    assert not world.pending_events() and not view.receipts


def test_loop_stop_with_no_unmet_work_is_never_cached(world):
    cid = load(world)
    HarnessEngine().investigate(world, cid, FakeLLM(), "SYNTHETIC-complete")
    assert not HarnessEngine()._unmet(world, cid)
    engine = HarnessEngine(config=HarnessConfig(max_steps=3))
    events = world.pending_events()
    responses = [
        LLMResponse(
            model_id="SYNTHETIC-scripted",
            mode="fake",
            tool_calls=[{"id": f"call-{i}", "name": "run_rules", "arguments": {}}],
        )
        for i in range(2 * len(events))
    ]
    engine.handle(world, ScriptedLLM(responses), "SYNTHETIC-loop")
    stops = [
        t for t in world.history(cid).traces if t.run_id == "SYNTHETIC-loop" and t.kind == "budget"
    ]
    assert len(stops) == len(events)
    assert all(t.result == {"reason": "loop", "unmet": []} for t in stops)
    assert world.view(cid).status == "needs_human"
    assert not any(
        "investigation_reused_from" in (t.result or {}) for t in world.history(cid).traces
    )


def test_event_ack_failure_does_not_retain_success_cache(world, monkeypatch):
    cid = load(world)
    pending = world.pending_events()
    before = world.view(cid)
    traces_before = world.history(cid).traces

    def fail(event_id):
        raise RuntimeError("SYNTHETIC acknowledgment failure")

    engine = HarnessEngine()
    llm = CountInvestigations()
    with monkeypatch.context() as patch:
        patch.setattr(world, "mark_event", fail)
        with pytest.raises(RuntimeError, match="acknowledgment failure"):
            engine.handle(world, llm, "SYNTHETIC-rollback")
    assert world.view(cid) == before
    assert world.pending_events() == pending
    assert world.history(cid).traces == traces_before
    engine.handle(world, llm, "SYNTHETIC-retry")
    assert llm.starts == 2
    assert not world.pending_events()


@pytest.mark.parametrize("change", ["ledger", "clock"])
def test_changed_ledger_or_clock_during_drain_invalidates_reuse(world, monkeypatch, change):
    cid = load(world)
    original = world.mark_event
    injected = False

    def acknowledge(event_id):
        nonlocal injected
        original(event_id)
        if injected:
            return
        injected = True
        if change == "clock":
            world.advance_to(1)
        else:
            credit = next(p for p in world.view(cid).proposals if p.kind == "credit_memo")
            world.approve(credit.proposal_id, credit.version, "SYNTHETIC reviewer")
            world.submit(credit.proposal_id, credit.version)

    monkeypatch.setattr(world, "mark_event", acknowledge)
    llm = CountInvestigations(limit=2)
    HarnessEngine().handle(world, llm, "SYNTHETIC-changed-state")
    assert llm.starts == 2
    assert not world.pending_events()
    assert not HarnessEngine()._unmet(world, cid)
    if change == "ledger":
        assert len(world.view(cid).receipts) == 1
        assert world.ledger_balance(cid).cents == 444000
        assert not any(
            p.kind == "credit_memo" and p.status == "proposed" for p in world.view(cid).proposals
        )


def test_recording_conflicts_and_original_bytes_remain_strict(tmp_path):
    recorder = ReplayLLM("SYNTHETIC-model", tmp_path)
    response = LLMResponse(model_id="SYNTHETIC-model", mode="live", tool_calls=[], latency_ms=12)
    request = ("SYNTHETIC system", [], [])
    recorder.record(*request, response)
    path = next(tmp_path.glob("*.json"))
    original = path.read_bytes()
    for changes in ({"latency_ms": 13}, {"text": "different response"}):
        with pytest.raises(ValueError, match="Conflicting replay recording"):
            recorder.record(*request, response.model_copy(update=changes))
        assert path.read_bytes() == original
    assert recorder.next(*request) == response.model_copy(update={"mode": "replay"})
