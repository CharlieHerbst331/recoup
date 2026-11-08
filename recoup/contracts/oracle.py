"""Contracts from design/02 §8.1."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .models import (
    ActionAttempt,
    CaseHistory,
    CaseView,
    Citation,
    Evidence,
    FactRevision,
    FactSet,
    ItemStatus,
    LoadResult,
    ProposalKind,
    TraceEvent,
    Verdict,
)


class StaticLineOut(BaseModel):
    line_id: str
    verdict: Verdict
    valid_cents: int | None
    disputed_cents: int | None
    citations: list[Citation]


class StaticProposalOut(BaseModel):
    kind: ProposalKind
    line_ids: list[str]
    amount_cents: int | None


class StaticClaimItemOut(BaseModel):
    item_id: str
    status: ItemStatus


class StaticOutput(BaseModel):
    case_id: str
    lines: list[StaticLineOut]
    proposals: list[StaticProposalOut]
    missing: dict[str, list[str]]
    notice_deadline: date | None
    claim_items: list[StaticClaimItemOut] = []


class LineOracle(BaseModel):
    line_id: str
    verdict: Verdict
    valid_cents: int | None
    disputed_cents: int | None
    required_refs: list[str]
    acceptable_refs: list[str]
    missing: list[str] = []


class CaseOracle(BaseModel):
    case_id: str
    expected_status: Literal["loaded", "quarantined"]
    lines: list[LineOracle]
    proposals: list[StaticProposalOut]
    forbidden_kinds: list[ProposalKind]
    notice_deadline: date | None
    claim_items: dict[str, ItemStatus] = {}
    oracle_sentinel: str


class EpisodeOracle(BaseModel):
    episode_id: str
    family: Literal["C1", "C2", "C3", "C4", "C5", "C6"]
    base_scenario_id: str
    mutation: str
    expected_receipts: list[dict]
    expected_open_balance_cents: int
    min_decision_versions: int
    required_observations: list[str]
    forbidden: list[str]
    deadline: date | None
    claim_items: dict[str, ItemStatus] = {}
    oracle_sentinel: str


class StaticRunRecord(BaseModel):
    arm: str
    case_id: str
    load: LoadResult
    output: StaticOutput | None
    error: str | None
    context: StaticCaseContext
    input_sha256: str
    output_basis_hash: str | None
    bases: list[FactSet]
    inventory: list[Evidence]
    facts: list[FactRevision]
    model_requests: list[dict]
    attempts: list[ActionAttempt]
    traces: list[TraceEvent]


class EpisodeRunRecord(BaseModel):
    arm: str
    episode_id: str
    history: CaseHistory
    final_view: CaseView
    traces: list[TraceEvent]
    stop_reason: str
    bases: list[FactSet]


class StaticCaseContext(BaseModel):
    case_id: str
    start_date: date
    sim_day: int
    sim_now: date


StaticRunRecord.model_rebuild()
