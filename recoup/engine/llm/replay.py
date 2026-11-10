"""Exact recorded-response replay; design/02 §5.9."""

import json
from hashlib import sha256
from pathlib import Path

from recoup.contracts.interfaces import LLMResponse
from recoup.engine.config import PROMPT_VERSION


def recording_key(prompt_version, model, system, messages, tools):
    payload = [prompt_version, model, system, messages, tools]
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class ReplayLLM:
    mode = "replay"

    def __init__(self, model, directory="runs/recordings", prompt_version=PROMPT_VERSION):
        if not model:
            raise ValueError("Replay requires the recorded model")
        self.model_id = model
        self.directory = Path(directory)
        self.prompt_version = prompt_version

    def _path(self, system, messages, tools):
        return self.directory / (
            recording_key(self.prompt_version, self.model_id, system, messages, tools) + ".json"
        )

    def record(self, system, messages, tools, response: LLMResponse):
        if response.mode != "live" or response.model_id != self.model_id:
            raise ValueError("Only matching live responses may be recorded")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(system, messages, tools)
        content = response.model_dump_json()
        # Never silently overwrite a different recording of the same request.
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != content:
                raise ValueError("Conflicting replay recording") from None

    def next(self, system, messages, tools) -> LLMResponse:
        response = LLMResponse.model_validate_json(
            self._path(system, messages, tools).read_text(encoding="utf-8")
        )
        if response.model_id != self.model_id or response.mode != "live":
            raise ValueError("Invalid live recording")
        return response.model_copy(update={"mode": "replay"})
