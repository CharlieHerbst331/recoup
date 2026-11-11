"""Official SDK adapter and live recording; design/02 §5.9."""

import json
import os
from copy import deepcopy
from time import monotonic

from recoup.contracts.interfaces import LLMResponse
from recoup.engine.config import PROMPT_VERSION
from recoup.engine.llm.errors import InvalidResponse, ProviderUnavailable
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
            from openai import OpenAI, OpenAIError

            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
                    timeout=timeout,
                    max_retries=0,
                )
            except OpenAIError:
                raise ValueError(
                    "Live client configuration unavailable; check API credentials"
                ) from None
        self.client = client
        self.timeout = timeout
        self.recorder = ReplayLLM(self.model_id, directory, prompt_version)

    def next(self, system, messages, tools) -> LLMResponse:
        return self._next(system, messages, tools)

    def next_with_timeout(self, system, messages, tools, timeout) -> LLMResponse:
        return self._next(system, messages, tools, timeout=min(self.timeout, timeout))

    def _next(self, system, messages, tools, *, timeout=None) -> LLMResponse:
        # Snapshot once so serialization and replay refer to the same request.
        messages, tools = deepcopy(messages), deepcopy(tools)
        request = {"model": self.model_id, "messages": _messages(system, messages)}
        if timeout is not None:
            request["timeout"] = timeout
        if tools:
            request["tools"] = [{"type": "function", "function": tool} for tool in tools]
            request["tool_choice"] = "auto"
        started = monotonic()
        from openai import APIConnectionError, APIResponseValidationError, APIStatusError

        try:
            completion = self.client.chat.completions.create(**request)
        except APIStatusError as exc:
            # Never expose provider bodies/headers (which can echo credentials).
            raise ProviderUnavailable(f"HTTP {exc.status_code}; no retry") from None
        except (APIConnectionError, TimeoutError, ConnectionError):
            raise ProviderUnavailable("connection or timeout; no retry") from None
        except (APIResponseValidationError, ValueError):
            raise InvalidResponse("Invalid provider response") from None
        latency_ms = max(0, int((monotonic() - started) * 1000))
        choices = getattr(completion, "choices", None)
        if not isinstance(choices, list) or len(choices) != 1:
            raise InvalidResponse("Expected one completion choice")
        choice = choices[0]
        if choice.finish_reason not in {"stop", "tool_calls"}:
            raise InvalidResponse("Incomplete or filtered completion")
        message = choice.message
        if message is None:
            raise InvalidResponse("Missing completion message")
        calls = []
        for call in message.tool_calls or []:
            function = getattr(call, "function", None)
            arguments = getattr(function, "arguments", None)
            try:
                parsed = json.loads(arguments, parse_constant=_reject_constant)
                json.dumps(parsed, allow_nan=False)
                arguments = parsed
            except (ValueError, TypeError):
                pass  # Preserve the invalid value for the trace and bounded rejection.
            item = {
                "id": getattr(call, "id", None),
                "name": getattr(function, "name", None),
                "arguments": arguments,
            }
            if getattr(call, "type", None) != "function":
                item["type"] = getattr(call, "type", None)
            calls.append(item)
        usage = getattr(completion, "usage", None)
        response = LLMResponse(
            tool_calls=calls,
            text=message.content or getattr(message, "refusal", None) or "",
            model_id=self.model_id,
            mode=self.mode,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=latency_ms,
        )
        try:
            self.recorder.record(system, messages, tools, response)
        except (OSError, ValueError):
            raise ProviderUnavailable("recording unavailable or conflicting; no retry") from None
        return response
