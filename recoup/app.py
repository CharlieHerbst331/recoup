"""Composition facade from design/02 §4.4–4.5; injectable unit lane: r10 design/04 §4."""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from importlib.util import find_spec
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.interfaces import (
    Controller,
    EngineParts,
    GateError,
    LLMClient,
    ScopedController,
    ToolSession,
    World,
)
from recoup.contracts.models import (
    Approval,
    CaseHistory,
    CaseView,
    DomainEvent,
    Evidence,
    FactRevision,
    GateIssue,
    LoadResult,
    Proposal,
    ProposalKind,
    Receipt,
    Verdict,
)
from recoup.contracts.oracle import CaseOracle, StaticOutput
from recoup.contracts.remittance import RemittanceBundle, RemittanceLoadResult


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
        root = Path(cases_dir)
        if not root.is_dir():
            raise FileNotFoundError(f"Regression directory does not exist: {root}")
        directories = sorted(path for path in root.iterdir() if path.is_dir())
        if not directories:
            raise FileNotFoundError(f"No regression case directories in {root}")
        results = []
        for directory in directories:
            case_id = directory.name
            service = None
            try:
                bundle = CaseBundle.model_validate_json((directory / "bundle.json").read_text())
                case_id = bundle.case_id
                service = build(self.config.model_copy(update={"db": ":memory:"}))
                loaded = service.world.load_bundle(bundle, str(directory))
                output = None
                if loaded.status == "loaded":
                    service.world.advance_to(bundle.static_day, release_events=False)
                    service.run(bundle.case_id)
                    output = service.static_output(bundle.case_id)
                # Oracles never enter World, a controller, an LLM request or a tool session.
                oracle = CaseOracle.model_validate_json((directory / "oracle.json").read_text())
                errors = []
                if oracle.case_id != bundle.case_id or loaded.case_id != bundle.case_id:
                    errors.append("case_id mismatch")
                if loaded.status != oracle.expected_status:
                    errors.append(f"status: expected {oracle.expected_status}, got {loaded.status}")
                if oracle.expected_status == "loaded" and output is not None:
                    errors.extend(_compare_regression(service.world, output, oracle))
                results.append((case_id, not errors, errors))
            except Exception as exc:
                results.append((case_id, False, [f"{type(exc).__name__}: {exc}"]))
            finally:
                if service is not None:
                    close = getattr(service.world, "close", None)
                    if close is not None:
                        close()
        return results

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
            if not isinstance(self.controller, ScopedController):
                raise GateError(
                    [
                        GateIssue(
                            code="controller_scope_unsupported",
                            message="Selected-case runs require a controller with scope(case_ids)",
                        )
                    ]
                )
            with self.controller.scope([case_id]):
                self._react([])
        else:
            self._react([])
        return [self.world.view(case_id)] if case_id is not None else self.world.list_cases()

    def load_remittance(self, path: str) -> RemittanceLoadResult:
        source = Path(path)
        bundle = RemittanceBundle.model_validate_json(source.read_text(encoding="utf-8"))
        result = self.world.load_remittance(bundle, str(source.parent))
        if result.status == "loaded" and not result.replay:
            self._react()
        return result

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


def _compare_regression(world: World, output: StaticOutput, oracle: CaseOracle) -> list[str]:
    """Compare a runtime export with the gate oracle (design/02 §4.5, §8.1, §8.6)."""
    errors = []
    if output.case_id != oracle.case_id:
        errors.append("output case_id mismatch")
    actual = {line.line_id: line for line in output.lines}
    expected = {line.line_id: line for line in oracle.lines}
    if len(actual) != len(output.lines) or len(expected) != len(oracle.lines):
        errors.append("duplicate line ids")
    if actual.keys() != expected.keys():
        errors.append(f"line ids: expected {sorted(expected)}, got {sorted(actual)}")
    inventory = {row.evidence_id: row.doc_ref for row in world.history(oracle.case_id).evidence_all}
    for line_id in sorted(expected.keys() & actual.keys()):
        want, got = expected[line_id], actual[line_id]
        if (got.verdict, got.valid_cents, got.disputed_cents) != (
            want.verdict,
            want.valid_cents,
            want.disputed_cents,
        ):
            errors.append(f"{line_id}: verdict or cents mismatch")
        if want.verdict == Verdict.needs_info and not set(want.missing).issubset(
            output.missing.get(line_id, [])
        ):
            errors.append(f"{line_id}: missing items mismatch")
        cited = set()
        for citation in got.citations:
            try:
                world.resolve_citation(citation)
            except Exception as exc:
                errors.append(f"{line_id}: invalid citation: {exc}")
            doc_ref = inventory.get(citation.evidence_id)
            if doc_ref is None:
                errors.append(f"{line_id}: unknown citation evidence")
                continue
            reference = f"{doc_ref}#{citation.locator}"
            cited.add(reference)
            if reference not in want.acceptable_refs and doc_ref not in want.acceptable_refs:
                errors.append(f"{line_id}: unacceptable citation {reference}")
        for required in want.required_refs:
            if required not in cited and not any(ref.split("#", 1)[0] == required for ref in cited):
                errors.append(f"{line_id}: missing required citation {required}")

    def proposals(rows):
        return Counter(
            (row.kind.value, tuple(sorted(row.line_ids)), row.amount_cents) for row in rows
        )

    offered, required = proposals(output.proposals), proposals(oracle.proposals)
    if required - offered:
        errors.append("proposals mismatch")
    monetary = {
        ProposalKind.dispute.value,
        ProposalKind.credit_memo.value,
        ProposalKind.correction.value,
        ProposalKind.counteroffer.value,
    }
    if any(kind in monetary or amount is not None for kind, _, amount in offered - required):
        errors.append("extra money-moving proposal")
    if any(row.kind in oracle.forbidden_kinds for row in output.proposals):
        errors.append("forbidden proposal kind")
    if output.notice_deadline != oracle.notice_deadline:
        errors.append("notice_deadline mismatch")
    items = {item.item_id: item.status for item in output.claim_items}
    expected_item_ids = [
        item.item_id for item in output.claim_items if item.item_id in oracle.claim_items
    ]
    if len(set(expected_item_ids)) != len(expected_item_ids):
        errors.append("duplicate claim item ids")
    if any(items.get(item_id) != status for item_id, status in oracle.claim_items.items()):
        errors.append("claim_items mismatch")
    return errors


class _ScopedHarnessController:
    """Composition adapter for the additive scoped-controller port (§4.5)."""

    def __init__(self, delegate: Controller, parts: EngineParts, llm: LLMClient) -> None:
        self.delegate, self.parts, self.llm = delegate, parts, llm
        self.name = delegate.name
        self._case_ids: tuple[str, ...] | None = None

    @contextmanager
    def scope(self, case_ids: list[str]):
        if (
            not case_ids
            or len(set(case_ids)) != len(case_ids)
            or any(not isinstance(case_id, str) or not case_id for case_id in case_ids)
        ):
            raise ValueError("A case scope requires distinct nonempty case IDs")
        previous = self._case_ids
        self._case_ids = tuple(case_ids)
        try:
            yield
        finally:
            self._case_ids = previous

    def react(self, world: World, events: list[DomainEvent], run_id: str) -> None:
        if self._case_ids is None:
            self.delegate.react(world, events, run_id)
            return
        if events:
            raise GateError(
                [
                    GateIssue(
                        code="controller_scope_events",
                        message="Scoped runs use an empty event list",
                    )
                ]
            )
        for case_id in self._case_ids:
            world.view(case_id)
        with world.transaction():
            for case_id in self._case_ids:
                self.parts.engine.investigate(world, case_id, self.llm, run_id)


def build(config: RecoupConfig | None = None, controller: Controller | None = None) -> Recoup:
    """Assemble §4.5 providers; absent engine packages retain the explicit G1 runtime."""
    from recoup.contracts.testing import NullController, ScriptedLLM, stub_parts
    from recoup.world.store import SqliteWorld

    config = config if config is not None else RecoupConfig.from_env()
    if find_spec("recoup.engine") is None:
        if config.llm != "fake":
            raise NotImplementedError(
                "Replay/live require Sonny's recoup.engine.factory; "
                "contract stubs support fake only"
            )
        parts = stub_parts()
        selected_controller = controller if controller is not None else NullController()
        llm = ScriptedLLM(())
        provider = "contract-stubs"
    else:
        # Installed-provider errors must propagate; never hide them with a stub fallback.
        from recoup.engine.factory import build_engine, get_llm, harness_controller

        parts = build_engine(config)
        if controller is None:
            llm = get_llm(config)
            selected_controller = _ScopedHarnessController(
                harness_controller(parts, llm), parts, llm
            )
        else:
            selected_controller = controller
            llm = ScriptedLLM(())
        provider = "engine"
    world = SqliteWorld(config.db, ingestor=parts.ingestor, validator=parts.validator)
    world.attempt_controller = selected_controller.name
    service = Recoup(
        config,
        world,
        selected_controller,
        parts,
        llm,
        next_due_day=world.next_due_day,
    )
    service.runtime_provider = provider
    return service
