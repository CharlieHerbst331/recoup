"""Offline SDK-shaped adapter checks; design/02 §4.5, §5.9."""

from copy import deepcopy
from types import SimpleNamespace as NS

import pytest
from openai.types.chat import ChatCompletion

from recoup.contracts.interfaces import LLMClient
from recoup.contracts.tools import tool_json_schemas
from recoup.engine.factory import get_llm
from recoup.engine.llm.openai_compat import OpenAICompatLLM
from recoup.engine.llm.replay import ReplayLLM


def completion(*, calls=None, text=None, usage=True, finish="tool_calls"):
    return ChatCompletion.model_validate(
        {
            "id": "synthetic-completion",
            "object": "chat.completion",
            "created": 0,
            "model": "synthetic-model-snapshot",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish,
                    "message": {"role": "assistant", "content": text, "tool_calls": calls},
                }
            ],
            "usage": {"prompt_tokens": 23, "completion_tokens": 7, "total_tokens": 30}
            if usage
            else None,
        }
    )


def call(name="end", arguments="{}", id="synthetic-call"):
    return {"id": id, "type": "function", "function": {"name": name, "arguments": arguments}}


class StubClient:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []
        self.chat = NS(completions=NS(create=self.create))

    def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Network forbidden in adapter tests")

    monkeypatch.setattr("socket.socket.connect", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


def test_tool_round_trip_and_exact_replay(tmp_path):
    tools = tool_json_schemas()
    messages = [{"role": "user", "content": "SYNTHETIC evidence"}]
    original = deepcopy((messages, tools))
    client = StubClient(
        completion(calls=[call("read_evidence", '{"evidence_id":"synthetic"}')]),
        completion(calls=[call()]),
    )
    live: LLMClient = OpenAICompatLLM("synthetic-model", client=client, directory=tmp_path)
    result = live.next("SYNTHETIC system", messages, tools)
    assert (messages, tools) == original
    assert result.mode == "live" and result.model_id == "synthetic-model"
    assert result.input_tokens == 23 and result.output_tokens == 7
    assert result.latency_ms >= 0
    assert result.tool_calls == [
        {"id": "synthetic-call", "name": "read_evidence", "arguments": {"evidence_id": "synthetic"}}
    ]
    request = client.requests[0]
    assert request["messages"] == [{"role": "system", "content": "SYNTHETIC system"}, *messages]
    assert request["tools"] == [{"type": "function", "function": t} for t in tools]
    assert request["tool_choice"] == "auto"
    replay = ReplayLLM("synthetic-model", tmp_path)
    recorded = replay.next("SYNTHETIC system", messages, tools)
    assert recorded == result.model_copy(update={"mode": "replay"})
    messages.extend(
        [
            {"role": "assistant", "content": result.text, "tool_calls": result.tool_calls},
            {
                "role": "tool",
                "tool_call_id": "synthetic-call",
                "name": "read_evidence",
                "content": "{}",
            },
        ]
    )
    live.next("SYNTHETIC system", messages, tools)
    assert client.requests[1]["messages"][-2]["tool_calls"] == [
        call("read_evidence", '{"evidence_id": "synthetic"}')
    ]
    assert client.requests[1]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "synthetic-call",
        "content": "{}",
    }
    assert len(list(tmp_path.glob("*.json"))) == 2
    with pytest.raises(FileNotFoundError):
        replay.next("different", messages, tools)
    assert len(client.requests) == 2


def test_text_without_usage_and_empty_tools(tmp_path):
    client = StubClient(completion(text="SYNTHETIC review", usage=False, finish="stop"))
    result = OpenAICompatLLM("m", client=client, directory=tmp_path).next("s", [], [])
    assert result.text == "SYNTHETIC review" and result.tool_calls == []
    assert result.input_tokens is None and result.output_tokens is None
    assert client.requests == [{"model": "m", "messages": [{"role": "system", "content": "s"}]}]


@pytest.mark.parametrize("arguments", ["{", "[]", "null", '"string"', '{"x":NaN}'])
def test_bad_arguments_never_recorded(tmp_path, arguments):
    client = StubClient(completion(calls=[call(arguments=arguments)]))
    with pytest.raises(ValueError):
        OpenAICompatLLM("m", client=client, directory=tmp_path).next("s", [], [])
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.parametrize("finish", ["length", "content_filter", "function_call"])
def test_partial_responses_never_recorded(tmp_path, finish):
    client = StubClient(completion(calls=[call()], finish=finish))
    with pytest.raises(ValueError, match="Incomplete"):
        OpenAICompatLLM("m", client=client, directory=tmp_path).next("s", [], [])
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.parametrize("calls", [[call(id="")], [call(), call()], [call(name="")]])
def test_invalid_call_identity(tmp_path, calls):
    with pytest.raises(ValueError):
        OpenAICompatLLM("m", client=StubClient(completion(calls=calls)), directory=tmp_path).next(
            "s", [], []
        )
    assert not list(tmp_path.glob("*.json"))


def test_multiple_calls_preserved(tmp_path):
    result = OpenAICompatLLM(
        "m", client=StubClient(completion(calls=[call(id="a"), call(id="b")])), directory=tmp_path
    ).next("s", [], [])
    assert [c["id"] for c in result.tool_calls] == ["a", "b"]


def test_client_error_propagates_without_record_or_fallback(tmp_path):
    client = StubClient(TimeoutError("synthetic timeout"))
    with pytest.raises(TimeoutError):
        OpenAICompatLLM("m", client=client, directory=tmp_path).next("s", [], [])
    assert len(client.requests) == 1
    assert not list(tmp_path.glob("*.json"))


def test_empty_choices_fail_closed(tmp_path):
    response = completion()
    response.choices = []
    with pytest.raises(ValueError, match="one completion"):
        OpenAICompatLLM("m", client=StubClient(response), directory=tmp_path).next("s", [], [])


def test_env_sdk_configuration_and_factory(monkeypatch, tmp_path):
    created = []
    client = StubClient(completion(text="SYNTHETIC", finish="stop"))

    def sdk(**kwargs):
        created.append(kwargs)
        return client

    monkeypatch.setattr("openai.OpenAI", sdk)
    monkeypatch.setenv("RECOUP_MODEL", "environment-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://synthetic.invalid/v1")
    live = OpenAICompatLLM(api_key="synthetic-key", directory=tmp_path)
    assert live.model_id == "environment-model"
    assert created[-1] == {
        "api_key": "synthetic-key",
        "base_url": "https://synthetic.invalid/v1",
        "timeout": 30,
        "max_retries": 0,
    }
    selected = get_llm(
        NS(llm="live", model="explicit-model", base_url="https://override.invalid/v1")
    )
    assert isinstance(selected, OpenAICompatLLM) and selected.client is client
    assert selected.model_id == "explicit-model"
    assert created[-1]["base_url"] == "https://override.invalid/v1"
    assert created[-1]["api_key"] is None  # SDK reads OPENAI_API_KEY.
    assert not client.requests  # Construction never makes a completion request.


def test_required_model_and_timeout(monkeypatch):
    monkeypatch.delenv("RECOUP_MODEL", raising=False)
    with pytest.raises(ValueError, match="requires"):
        OpenAICompatLLM(client=StubClient())
    with pytest.raises(ValueError, match="positive"):
        OpenAICompatLLM("m", client=StubClient(), timeout=0)


def test_real_sdk_reads_key_without_network(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    live = OpenAICompatLLM("m", directory=tmp_path)
    try:
        assert live.client.api_key == "synthetic-key"
        assert live.client.max_retries == 0
    finally:
        live.client.close()
