"""SYNTHETIC HTTP responses, never live evidence; design/02 §5.1–5.2, §5.9."""

import json

import httpx2 as httpx
import pytest
from openai import OpenAI

from recoup.engine.config import HarnessConfig
from recoup.engine.harness import HarnessEngine
from recoup.engine.llm.openai_compat import OpenAICompatLLM
from recoup.engine.llm.replay import ReplayLLM

from .test_007_4_integration import load
from .test_openai_compat import call, completion, no_network  # noqa: F401


@pytest.fixture
def world():
    from recoup.app import RecoupConfig, build
    from recoup.contracts.testing import NullController

    service = build(RecoupConfig(db=":memory:", llm="fake"), controller=NullController())
    try:
        yield service.world
    finally:
        service.world.close()


def adapter(tmp_path, handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAI(
        api_key="SYNTHETIC",
        base_url="https://synthetic.invalid/v1",
        http_client=http,
        max_retries=0,
    )
    return OpenAICompatLLM("SYNTHETIC", client=client, directory=tmp_path)


def run(world, llm, **limits):
    return HarnessEngine(config=HarnessConfig(**limits)).investigate(
        world, load(world), llm, "SYNTHETIC-http-run"
    )


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
def test_http_failure_stops_once_without_leaking_body(world, tmp_path, status):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            status, json={"error": {"message": "SYNTHETIC-secret"}}, headers={"retry-after": "60"}
        )

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm)
        assert result.status == "needs_human"
        assert f"HTTP {status}; no retry" in result.status_reason
        assert "SYNTHETIC-secret" not in result.model_dump_json()
        assert len(requests) == 1
        assert requests[0]["model"] == "SYNTHETIC"
        budget = world.history(result.case_id).traces[-1]
        assert budget.llm_mode == "live" and budget.model_id == "SYNTHETIC"
        assert not result.decision and not result.receipts
        assert not list(tmp_path.glob("*.json"))
    finally:
        llm.client.close()


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_failure_never_retried(world, tmp_path, error):
    requests = []

    def handler(request):
        requests.append(request)
        raise error("SYNTHETIC-secret", request=request)

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm)
        assert "connection or timeout; no retry" in result.status_reason
        assert len(requests) == 1
        assert "SYNTHETIC-secret" not in result.model_dump_json()
    finally:
        llm.client.close()


@pytest.mark.parametrize(
    "calls",
    [
        [call(arguments="{")],
        [call(arguments="[]")],
        [call(arguments="null")],
        [call(arguments='{"x":NaN}')],
        [call(arguments='{"x":1e999}')],
        [call(id="")],
        [call(), call()],
        [call(name="")],
        [call(), call(arguments="{")],
        [{"type": "function", "function": {"name": "run_rules", "arguments": "{}"}}],
    ],
)
def test_malformed_batch_recorded_but_never_executed(world, tmp_path, calls):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        # Raw wire data also exercises SDK handling of omitted call IDs.
        body = completion().model_dump()
        body["choices"][0]["message"]["tool_calls"] = calls
        return httpx.Response(200, json=body)

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm, max_tool_errors=2)
        assert "tool errors" in result.status_reason
        traces = world.history(result.case_id).traces
        models = [t for t in traces if t.kind == "model_call"]
        assert len(models) == 2 and len(requests) == 2
        assert not any(t.kind == "tool_call" for t in traces)
        assert not result.decision and not result.receipts
        assert not any(m.get("tool_calls") for m in requests[1]["messages"])
        replay = ReplayLLM("SYNTHETIC", tmp_path)
        for trace in models:
            response = replay.next(**trace.request)
            assert response.tool_calls == trace.result["tool_calls"]
    finally:
        llm.client.close()


def test_text_only_is_recorded_and_bounded_without_usage(world, tmp_path):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200, json=completion(text="SYNTHETIC review", usage=False, finish="stop").model_dump()
        )

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm)
        assert "tool errors" in result.status_reason
        assert len(requests) == 4
        models = [t for t in world.history(result.case_id).traces if t.kind == "model_call"]
        assert all(t.input_tokens is None and t.output_tokens is None for t in models)
        assert any(
            m["content"] == "Call a tool to continue or end." for m in requests[1]["messages"]
        )
    finally:
        llm.client.close()


def test_recovery_serializes_only_valid_tool_history_and_keeps_work(world, tmp_path):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            response = completion(calls=[call("run_rules", id="rules")])
        elif len(requests) == 2:
            response = completion(calls=[call(arguments="{")])
        else:
            response = completion(calls=[call("list_evidence", id="inventory")])
        return httpx.Response(200, json=response.model_dump())

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm, max_steps=3)
        assert "steps" in result.status_reason
        traces = world.history(result.case_id).traces
        assert [t.tool for t in traces if t.kind == "tool_call"] == ["run_rules", "list_evidence"]
        history = requests[-1]["messages"]
        calls = [c for m in history for c in m.get("tool_calls", [])]
        assert calls == [call("run_rules", id="rules")]
        results = [m for m in history if m["role"] == "tool"]
        assert len(results) == 1 and results[0]["tool_call_id"] == "rules"
        assert json.loads(results[0]["content"])["ok"] is True
        assert not result.receipts
    finally:
        llm.client.close()


@pytest.mark.parametrize("finish", ["length", "content_filter"])
def test_partial_completion_uses_error_budget_without_tool_work(world, tmp_path, finish):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=completion(calls=[call()], finish=finish).model_dump())

    llm = adapter(tmp_path, handler)
    try:
        result = run(world, llm, max_tool_errors=2)
        assert "tool errors" in result.status_reason and len(requests) == 2
        assert not any(t.kind == "tool_call" for t in world.history(result.case_id).traces)
        assert not list(tmp_path.glob("*.json"))
    finally:
        llm.client.close()
