"""G1 smoke requires the real provider; a skip is BLOCKED, never integration PASS."""

from importlib.util import find_spec

import pytest


def test_build_real_sqlite_world_with_contract_stubs():
    if find_spec("recoup.world") is None:
        pytest.skip("BLOCKED G1: real SqliteWorld provider requires 006-2B")
    from recoup.world.store import SqliteWorld

    from recoup.app import RecoupConfig, build
    from recoup.contracts.testing import NullController

    controller = NullController()
    app = build(RecoupConfig(db=":memory:"), controller=controller)
    assert isinstance(app.world, SqliteWorld)
    assert app.controller is controller
    assert app.world.list_cases() == []
