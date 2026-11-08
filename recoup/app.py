"""Composition facade from design/02 §4.4–4.5; injectable unit lane: r10 design/04 §4."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import Controller, EngineParts, LLMClient, ToolSession, World
from recoup.contracts.models import (
    Approval,
    CaseHistory,
    CaseView,
    DomainEvent,
    Evidence,
    FactRevision,
    LoadResult,
    Proposal,
    Receipt,
)
from recoup.contracts.oracle import StaticOutput


class RecoupConfig(BaseModel):
    db: str = "runs/recoup.db"
    llm: Literal["fake", "replay", "live"] = "fake"
    model: str | None = None
    base_url: str | None = None
    vision: bool = False
    run_id: str | None = None

    @classmethod
    def from_env(cls) -> RecoupConfig:
        names = {
            "db": "RECOUP_DB",
            "llm": "RECOUP_LLM",
            "model": "RECOUP_MODEL",
            "base_url": "OPENAI_BASE_URL",
            "vision": "RECOUP_VISION",
        }
        return cls.model_validate(
            {field: os.environ[name] for field, name in names.items() if name in os.environ}
        )


class Recoup:
    def __init__(
        self,
        config: RecoupConfig,
        world: World,
        controller: Controller,
        parts: EngineParts,
        llm: LLMClient,
        *,
        next_due_day: Callable[[], int | None] | None = None,
    ) -> None:
        self.config = config.model_copy(deep=True)
        if self.config.run_id is None:
            self.config.run_id = str(uuid4())
        self.world = world
        self.controller = controller
        self.llm = llm
        self._parts = parts
        self._next_due_day = next_due_day

    def _react(self, events: list[DomainEvent] | None = None) -> None:
        self.controller.react(
            self.world,
            self.world.pending_events() if events is None else events,
            self.config.run_id,
        )

    def tool_session(self, case_id: str, run_id: str, controller: str) -> ToolSession:
        return self._parts.tools.open(self.world, case_id, run_id, controller)

    def static_output(self, case_id: str) -> StaticOutput:
        return self._parts.engine.static_output(self.world, case_id)

    def rules_only(self, case_id: str) -> StaticOutput:
        return self._parts.engine.rules_only(self.world, case_id)

    def history(self, case_id: str) -> CaseHistory:
        return self.world.history(case_id)

    def check_regression(
        self, cases_dir: str = "cases/regression"
    ) -> list[tuple[str, bool, list[str]]]:
        raise NotImplementedError("Regression gate wiring awaits 006-4 fixtures and 006-5 CLI")

    def load(self, paths: list[str]) -> list[LoadResult]:
        bundles = []
        for name in paths:
            path = Path(name)
            if not path.is_dir():
                raise NotADirectoryError(path)
            files = (
                [path / "bundle.json"]
                if (path / "bundle.json").is_file()
                else sorted(path.glob("*/bundle.json"))
            )
            if not files:
                raise FileNotFoundError(f"No bundle.json in {path} or its immediate children")
            for file in files:
                bundles.append((CaseBundle.model_validate_json(file.read_text()), str(file.parent)))
        results = [self.world.load_bundle(bundle, directory) for bundle, directory in bundles]
        if results:
            self._react()
        return results

    def run(self, case_id: str | None = None) -> list[CaseView]:
        if case_id is not None:
            self.world.view(case_id)
        self._react([])
        return [self.world.view(case_id)] if case_id is not None else self.world.list_cases()

    def advance(self, days: int | None = None, to_next_due: bool = False) -> list[str]:
        if days is not None and to_next_due:
            raise ValueError("Specify days or to_next_due, not both")
        if days is not None and (type(days) is not int or days < 0):
            raise ValueError("days must be a nonnegative integer")
        start = self.world.clock.day()
        if to_next_due:
            target = self.next_due_day()
            if target is None:
                return []
            if type(target) is not int or target < start:
                raise ValueError("next_due_day must be an integer at or after the current day")
        else:
            target = start + (1 if days is None else days)
        if target == start:
            if to_next_due:
                self._react(self.world.pending_events())
                return [case.case_id for case in self.world.list_cases()]
            return []
        for day in range(start + 1, target + 1):
            self._react(self.world.advance_to(day))
        return [case.case_id for case in self.world.list_cases()]

    def add_evidence(
        self, case_id: str, doc: BundleDoc, bundle_dir: str | None = None
    ) -> Evidence | None:
        result = self.world.add_evidence(case_id, doc, bundle_dir)
        self._react()
        return result

    def confirm_field(self, evidence_id: str, key: str) -> FactRevision:
        result = self.world.confirm_field(evidence_id, key, "user")
        self._react()
        return result

    def edit(self, proposal_id: str, version: int, **changes) -> Proposal:
        result = self.world.edit_proposal(proposal_id, version, **changes)
        self._react()
        return result

    def approve(self, proposal_id: str, version: int, approver: str = "user") -> Approval:
        result = self.world.approve(proposal_id, version, approver)
        self._react()
        return result

    def reject(
        self, proposal_id: str, version: int, reason: str, approver: str = "user"
    ) -> Approval:
        result = self.world.reject(proposal_id, version, approver, reason)
        self._react()
        return result

    def submit(self, proposal_id: str, version: int) -> Receipt:
        result = self.world.submit(proposal_id, version)
        self._react()
        return result

    def next_due_day(self) -> int | None:
        if self._next_due_day is None:
            raise NotImplementedError("World due-work/held-event lookup awaits 006-2B")
        return self._next_due_day()


def build(config: RecoupConfig | None = None, controller: Controller | None = None) -> Recoup:
    """G1 stub assembly; importing this module does not require a production World.

    The real provider belongs to 006-2B. A missing/broken provider propagates its
    import error; no substitute World or engine factory is installed here.
    """
    from recoup.contracts.testing import NullController, ScriptedLLM, stub_parts
    from recoup.world.store import SqliteWorld

    config = config if config is not None else RecoupConfig.from_env()
    if config.llm != "fake":
        raise NotImplementedError("Replay/live assembly awaits 006-5; G1 uses contract stubs")
    parts = stub_parts()
    world = SqliteWorld(config.db, ingestor=parts.ingestor, validator=parts.validator)
    return Recoup(
        config,
        world,
        controller if controller is not None else NullController(),
        parts,
        ScriptedLLM(()),
    )
