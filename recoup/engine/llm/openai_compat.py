"""Official SDK adapter and live recording; design/02 §5.9."""

import json
import os
from copy import deepcopy
from time import monotonic

from recoup.contracts.interfaces import LLMResponse
from recoup.engine.config import PROMPT_VERSION
from recoup.engine.llm.replay import ReplayLLM


def _messages(system, messages):
    result = [{"role": "system", "content": system}]
    for message in deepcopy(messages):
        if message["role"] == "assistant":
            calls = message.pop("tool_calls", None)
            if calls:
                message["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"], allow_nan=False),
                        },
                    }
                    for call in calls
                ]
        elif message["role"] == "tool":
            message.pop("name", None)
        result.append(message)
    return result


def _reject_constant(value):
    raise ValueError("Non-finite tool argument")


class OpenAICompatLLM:
    mode = "live"

    def __init__(
        self,
        model=None,
        *,
        base_url=None,
        api_key=None,
        client=None,
        directory="runs/recordings",
        prompt_version=PROMPT_VERSION,
        timeout=30,
    ):
        self.model_id = model or os.environ.get("RECOUP_MODEL")
        if not self.model_id or not self.model_id.strip():
            raise ValueError("Live mode requires RECOUP_MODEL or an explicit model")
        if timeout <= 0:
            raise ValueError("Live timeout must be positive")
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
                timeout=timeout,
                max_retries=0,
            )
        self.client = client
        self.recorder = ReplayLLM(self.model_id, directory, prompt_version)

    def next(self, system, messages, tools) -> LLMResponse:
        # Snapshot once so serialization and replay refer to the same request.
        messages, tools = deepcopy(messages), deepcopy(tools)
        request = {"model": self.model_id, "messages": _messages(system, messages)}
        if tools:
            request["tools"] = [{"type": "function", "function": tool} for tool in tools]
            request["tool_choice"] = "auto"
        started = monotonic()
        completion = self.client.chat.completions.create(**request)
        latency_ms = max(0, int((monotonic() - started) * 1000))
        if len(completion.choices) != 1:
            raise ValueError("Expected one completion choice")
        choice = completion.choices[0]
        if choice.finish_reason not in {"stop", "tool_calls"}:
            raise ValueError("Incomplete or filtered completion")
        message = choice.message
        calls = []
        ids = set()
        for call in message.tool_calls or []:
            if call.type != "function" or not call.id or call.id in ids:
                raise ValueError("Invalid function call identity")
            ids.add(call.id)
            if not call.function.name:
                raise ValueError("Missing function name")
            arguments = json.loads(call.function.arguments, parse_constant=_reject_constant)
            if not isinstance(arguments, dict):
                raise ValueError("Function arguments must be a JSON object")
            calls.append({"id": call.id, "name": call.function.name, "arguments": arguments})
        usage = completion.usage
        response = LLMResponse(
            tool_calls=calls,
            text=message.content or getattr(message, "refusal", None) or "",
            model_id=self.model_id,
            mode=self.mode,
            input_tokens=usage.prompt_tokens if usage is not None else None,
            output_tokens=usage.completion_tokens if usage is not None else None,
            latency_ms=latency_ms,
        )
        self.recorder.record(system, messages, tools, response)
        return response
