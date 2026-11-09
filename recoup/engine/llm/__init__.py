"""Offline adapters; design/02 §5.9."""

from .fake import FakeLLM
from .replay import ReplayLLM

__all__ = ["FakeLLM", "ReplayLLM"]
