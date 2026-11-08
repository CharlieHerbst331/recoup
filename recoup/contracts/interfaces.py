"""Contracts from design/02 §3.5."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from .bundle import BundleDoc, CaseBundle
from .models import (
    ActionAttempt,
    Approval,
    CaseHistory,
    CaseStatus,
    CaseView,
    Citation,
    Decision,
    DeductionLine,
    DeductionReason,
    DomainEvent,
    DueWork,
    Evidence,
    ExtractFailure,
    ExtractMethod,
    FactRevision,
    FactSet,
    FieldTrust,
    GateIssue,
    InsuranceStatus,
    LedgerEntry,
    LineAmount,
    LineReasonRevision,
    LoadResult,
    Money,
    Proposal,
    QuarantineRecord,
    Readiness,
    Receipt,
    Scalar,
    Target,
    TraceEvent,
)
from .oracle import StaticOutput
from .tools import ToolEnvelope


class GateError(Exception):
    def __init__(self, issues: list[GateIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{issue.code}: {issue.message}" for issue in issues))


class TransientError(Exception): ...


class Clock(Protocol):
    def now(self) -> datetime: ...
    def day(self) -> int: ...


class IngestOutput(BaseModel):
    text: str
    fields: dict[str, Scalar]
    field_trust: dict[str, FieldTrust]
    readable: bool
    method: ExtractMethod
    failure: ExtractFailure | None = None


@runtime_checkable
class Ingestor(Protocol):
    def ingest(self, doc: BundleDoc, bundle_dir: str | None) -> IngestOutput: ...


@runtime_checkable
class ProposalValidator(Protocol):
    def validate(
        self, world: "World", proposal: Proposal, stage: Literal["save", "approve", "submit"]
    ) -> list[GateIssue]: ...


class LLMResponse(BaseModel):
    tool_calls: list[dict]
    text: str = ""
    model_id: str
    mode: Literal["fake", "replay", "live"]
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0


class LLMClient(Protocol):
    def next(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


class World(Protocol):
    clock: Clock

    def load_bundle(self, bundle: CaseBundle, bundle_dir: str | None = None) -> LoadResult: ...
    def list_quarantined(self) -> list[QuarantineRecord]: ...
    def add_evidence(
        self, case_id: str, doc: BundleDoc, bundle_dir: str | None = None
    ) -> Evidence | None: ...
    def attach_held(self, case_id: str, system: str, query: str) -> list[Evidence]: ...
    def add_fact(
        self,
        evidence_id: str,
        key: str,
        value: Scalar,
        trust: FieldTrust,
        citation: Citation | None,
        by: str,
    ) -> FactRevision: ...
    def confirm_field(self, evidence_id: str, key: str, approver: str) -> FactRevision: ...
    def set_line_reason(
        self,
        case_id: str,
        line_id: str,
        reason: DeductionReason,
        trust: FieldTrust,
        citation: Citation | None,
    ) -> LineReasonRevision: ...
    def fact_set(self, case_id: str, basis_hash: str | None = None) -> FactSet: ...

    def resolve_citation(
        self, c: Citation, basis_hash: str | None = None
    ) -> Scalar | str | None: ...
    @contextmanager
    def transaction(self) -> Iterator[None]: ...

    def active_evidence(self, case_id: str) -> list[Evidence]: ...
    def evidence(self, evidence_id: str) -> Evidence: ...
    def evidence_set_hash(self, case_id: str) -> str: ...
    def deduction_lines(self, case_id: str) -> list[DeductionLine]: ...
    def ledger_balance(self, case_id: str) -> Money: ...
    def ledger(self, case_id: str) -> list[LedgerEntry]: ...
    def current_decision(self, case_id: str) -> Decision | None: ...
    def readiness(self, case_id: str) -> list[Readiness]: ...
    def view(self, case_id: str) -> CaseView: ...
    def history(self, case_id: str) -> CaseHistory: ...
    def list_cases(self) -> list[CaseView]: ...
    def allowed_recipients(self, case_id: str, target: Target) -> list[str]: ...

    def save_decision(self, d: Decision) -> Decision: ...
    def save_readiness(self, r: Readiness) -> Readiness: ...
    def save_proposal(self, p: Proposal) -> Proposal: ...
    def edit_proposal(
        self,
        proposal_id: str,
        version: int,
        *,
        draft_text: str | None = None,
        recipient: str | None = None,
        allocations: list[LineAmount] | None = None,
        editor: str = "user",
    ) -> Proposal: ...
    def approve(self, proposal_id: str, version: int, approver: str) -> Approval: ...
    def reject(self, proposal_id: str, version: int, approver: str, reason: str) -> Approval: ...
    def submit(self, proposal_id: str, version: int) -> Receipt: ...
    def set_status(
        self,
        case_id: str,
        status: CaseStatus | None = None,
        insurance: InsuranceStatus | None = None,
        reason: str = "",
    ) -> None: ...

    def advance_to(self, day: int, release_events: bool = True) -> list[DomainEvent]: ...
    def schedule(self, w: DueWork) -> DueWork: ...
    def cancel_due(self, case_id: str, kind: str, reason: str) -> int: ...
    def due(self, until: datetime) -> list[DueWork]: ...
    def mark_due(self, due_id: str, status: Literal["done", "cancelled"]) -> None: ...
    def pending_events(self) -> list[DomainEvent]: ...
    def mark_event(self, event_id: str) -> None: ...
    def trace(self, e: TraceEvent) -> None: ...
    def fail_next(self, target: str) -> None: ...
    def record_attempt(self, a: ActionAttempt) -> None: ...


@runtime_checkable
class Engine(Protocol):
    def investigate(self, world: World, case_id: str, llm: LLMClient, run_id: str) -> CaseView: ...
    def handle(self, world: World, llm: LLMClient, run_id: str) -> list[str]: ...
    def static_output(self, world: World, case_id: str) -> StaticOutput: ...
    def rules_only(self, world: World, case_id: str) -> StaticOutput: ...


class ToolSession(Protocol):
    def schemas(self) -> list[dict]: ...
    def call(self, name: str, args: dict) -> ToolEnvelope: ...


@runtime_checkable
class ToolSessionFactory(Protocol):
    def open(self, world: World, case_id: str, run_id: str, controller: str) -> ToolSession: ...


class Controller(Protocol):
    name: str

    def react(self, world: World, events: list[DomainEvent], run_id: str) -> None: ...


class EngineParts(BaseModel, arbitrary_types_allowed=True):
    engine: Engine
    ingestor: Ingestor
    validator: ProposalValidator
    tools: ToolSessionFactory
