"""Harness settings; design/02 §5.2, §5.9–5.10."""

from dataclasses import dataclass

PROMPT_VERSION = "v1"
MAX_STEPS = 16
MAX_TOOL_ERRORS = 4
MAX_WALL_S = 120


@dataclass(frozen=True)
class HarnessConfig:
    max_steps: int = MAX_STEPS
    max_tool_errors: int = MAX_TOOL_ERRORS
    max_wall_s: int = MAX_WALL_S

    def __post_init__(self):
        if not 1 <= self.max_steps <= MAX_STEPS:
            raise ValueError("max_steps outside treatment limit")
        if not 1 <= self.max_tool_errors <= MAX_TOOL_ERRORS:
            raise ValueError("max_tool_errors outside treatment limit")
        if not 0 < self.max_wall_s <= MAX_WALL_S:
            raise ValueError("max_wall_s outside treatment limit")
