"""UI tests use the facade and an offline in-memory World (design/02 §2)."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.testing import NullController

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def service():
    instance = build(RecoupConfig(db=":memory:", llm="fake"), controller=NullController())
    try:
        instance.load([str(ROOT / "cases" / "demo" / case_id) for case_id in ("H", "C", "N")])
        yield instance
    finally:
        instance.world.close()
