"""Owner-local behavior scripts only; no persistence or integration guarantees."""

from collections import deque
from datetime import datetime, timedelta

from recoup.contracts.models import FactSet


class ScriptedClock:
    def __init__(self, start: datetime, day: int = 0) -> None:
        self.start = start
        self.current_day = day

    def now(self) -> datetime:
        return self.start + timedelta(days=self.current_day)

    def day(self) -> int:
        return self.current_day


class ScriptedWorld:
    """Only fact_set is exercised at 007-0; other calls fail closed."""

    def __init__(self, clock: ScriptedClock, reads: list[tuple[str, str | None, FactSet]]) -> None:
        self.clock = clock
        self.reads = deque(reads)
        self.calls: list[tuple[str, str, str | None]] = []

    def fact_set(self, case_id: str, basis_hash: str | None = None) -> FactSet:
        self.calls.append(("fact_set", case_id, basis_hash))
        if not self.reads:
            raise NotImplementedError("Unexpected fact_set call")
        expected_case, expected_basis, result = self.reads.popleft()
        assert (case_id, basis_hash) == (expected_case, expected_basis)
        return result.model_copy(deep=True)

    def __getattr__(self, name: str):
        raise NotImplementedError(f"Unscripted World method: {name}")

    def assert_finished(self) -> None:
        assert not self.reads, "Unused fact_set calls"
