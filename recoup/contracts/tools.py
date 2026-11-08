"""Contracts from design/02 §3.4."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .models import (
    Basis,
    Citation,
    DeductionReason,
    DocKind,
    EffectiveFact,
    GateIssue,
    ProposalKind,
    Readiness,
    RuleFinding,
    Scalar,
    Verdict,
)


class ToolEnvelope(BaseModel):
    ok: bool
    result: dict | None
    issues: list[GateIssue] = []


class ListEvidenceArgs(BaseModel):
    kind: DocKind | None = None
    include_superseded: bool = False


class EvidenceIndexRow(BaseModel):
    evidence_id: str
    doc_ref: str
    version: int
    kind: DocKind
    title: str
    readable: bool
    method: str
    failure: str | None
    active: bool
    field_keys: list[str]
    text_chars: int


class ListEvidenceResult(BaseModel):
    rows: list[EvidenceIndexRow]


class ReadEvidenceArgs(BaseModel):
    evidence_id: str
    locator: str | None = None
    max_chars: int = 4000


class ReadEvidenceResult(BaseModel):
    evidence_id: str
    active: bool
    text: str
    truncated: bool
    source_fields: dict[str, Scalar]
    facts: list[EffectiveFact]


class SearchEvidenceArgs(BaseModel):
    query: str
    max_hits: int = 10


class SearchHit(BaseModel):
    evidence_id: str
    locator: str
    snippet: str


class SearchEvidenceResult(BaseModel):
    hits: list[SearchHit]


class GetLedgerArgs(BaseModel):
    pass


class GetLedgerResult(BaseModel):
    invoice_total_cents: int
    paid_cents: int
    posted_credit_cents: int
    open_balance_cents: int
    lines: list[dict]
    submitted_dispute_cents_by_line: dict[str, int]
    posted_credit_cents_by_line: dict[str, int]


class ClassifyLineArgs(BaseModel):
    line_id: str
    reason: DeductionReason
    citation: Citation


class ClassifyLineResult(BaseModel):
    line_id: str
    reason: DeductionReason
    accepted: bool


class ProposeFactArgs(BaseModel):
    evidence_id: str
    key: str
    value: Scalar
    citation: Citation


class ProposeFactResult(BaseModel):
    key: str
    accepted: bool
    trust: str


class RunRulesArgs(BaseModel):
    line_ids: list[str] | None = None


class RunRulesResult(BaseModel):
    findings: list[RuleFinding]


PolicyQuestion = Literal[
    "applicability",
    "notice_deadline",
    "claim_window",
    "claim_documents",
    "disputed_debt",
    "credit_limit",
    "exclusions",
]


class CheckPolicyArgs(BaseModel):
    question: PolicyQuestion


class PolicyAnswer(BaseModel):
    question: PolicyQuestion
    clause_key: str | None = None
    applies: bool | None
    value: str | None
    computed_date: date | None
    clause_citation: Citation | None
    basis: Basis
    note: str


class CheckPolicyResult(BaseModel):
    answers: list[PolicyAnswer]


class ReadinessArgs(BaseModel):
    kind: Literal["dispute", "notice", "claim"]
    line_id: str | None = None


class ReadinessResult(BaseModel):
    readiness: Readiness


class PlanMissingArgs(BaseModel):
    line_id: str | None = None


class MissingItem(BaseModel):
    line_id: str | None
    track: Literal["deduction", "insurance"]
    need: str
    why: str
    request_from: Literal["buyer", "carrier", "warehouse", "insurer", "internal"]
    blocking_for: list[str]


class PlanMissingResult(BaseModel):
    items: list[MissingItem]


class FetchArgs(BaseModel):
    system: Literal["erp", "shipping", "email", "insurer"]
    query: str


class FetchResult(BaseModel):
    status: Literal["found", "not_found", "transient_error"]
    new_evidence_ids: list[str]


class LineDecisionIn(BaseModel):
    line_id: str
    verdict: Verdict
    citations: list[Citation]
    rationale: str


class ProposeDecisionArgs(BaseModel):
    lines: list[LineDecisionIn]


class ProposeDecisionResult(BaseModel):
    accepted: bool
    decision_id: str | None
    decision_version: int | None
    per_line_issues: dict[str, list[GateIssue]]


class DraftProposalArgs(BaseModel):
    kind: ProposalKind
    line_ids: list[str] = []
    recipient: str
    draft_text: str
    citations: list[Citation]
    corrects_receipt_id: str | None = None


class DraftProposalResult(BaseModel):
    accepted: bool
    proposal_id: str | None
    version: int | None
    business_key: str | None
    amount_cents: int | None
    allocations: dict[str, int]
    issues: list[GateIssue]
    no_op: bool = False


class ScheduleFollowupArgs(BaseModel):
    kind: Literal["follow_up", "recheck"]
    days_from_now: int


class ScheduleFollowupResult(BaseModel):
    due_id: str
    due_at: str
    clamped: bool


class RequestApprovalArgs(BaseModel):
    proposal_id: str
    version: int


class RequestApprovalResult(BaseModel):
    queued: bool
    issues: list[GateIssue]


class EndArgs(BaseModel):
    reason: str


class EndResult(BaseModel):
    accepted: bool
    unmet: list[str]


class SubmitApprovedArgs(BaseModel):
    proposal_id: str
    version: int


class SubmitApprovedResult(BaseModel):
    receipt_id: str | None
    issues: list[GateIssue]


class WaitUntilArgs(BaseModel):
    day: int


class WaitUntilResult(BaseModel):
    sim_day: int
    released_evidence_ids: list[str]
    due_fired: list[str]


TOOL_REGISTRY: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "list_evidence": (ListEvidenceArgs, ListEvidenceResult),
    "read_evidence": (ReadEvidenceArgs, ReadEvidenceResult),
    "search_evidence": (SearchEvidenceArgs, SearchEvidenceResult),
    "get_ledger": (GetLedgerArgs, GetLedgerResult),
    "classify_line": (ClassifyLineArgs, ClassifyLineResult),
    "propose_fact": (ProposeFactArgs, ProposeFactResult),
    "run_rules": (RunRulesArgs, RunRulesResult),
    "check_policy": (CheckPolicyArgs, CheckPolicyResult),
    "readiness": (ReadinessArgs, ReadinessResult),
    "plan_missing_evidence": (PlanMissingArgs, PlanMissingResult),
    "fetch_from_system": (FetchArgs, FetchResult),
    "propose_decision": (ProposeDecisionArgs, ProposeDecisionResult),
    "draft_proposal": (DraftProposalArgs, DraftProposalResult),
    "schedule_followup": (ScheduleFollowupArgs, ScheduleFollowupResult),
    "request_approval": (RequestApprovalArgs, RequestApprovalResult),
    "end": (EndArgs, EndResult),
}
BENCH_TOOLS: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "submit_approved": (SubmitApprovedArgs, SubmitApprovedResult),
    "wait_until": (WaitUntilArgs, WaitUntilResult),
}
TOOL_DESCRIPTIONS: dict[str, str] = {
    "list_evidence": (
        "List case evidence, optionally filtering by kind or including superseded documents."
    ),
    "read_evidence": "Read one evidence document and its current effective facts.",
    "search_evidence": "Search the case's active evidence for matching text.",
    "get_ledger": "Read invoice, payment, credit and open balance amounts with deduction lines.",
    "classify_line": "Propose a cited deduction reason for one line.",
    "propose_fact": "Propose a quoted fact from an evidence document for validation.",
    "run_rules": "Compute rule findings for all or selected deduction lines.",
    "check_policy": "Answer one policy question using the case's policy facts and citations.",
    "readiness": "Check readiness for one dispute line, an insurer notice or a claim package.",
    "plan_missing_evidence": "List missing evidence and where to request it.",
    "fetch_from_system": "Attach released matching documents from a mock system.",
    "propose_decision": "Propose cited line verdicts for validation against the rules.",
    "draft_proposal": "Draft an action whose amounts are derived and validated by code.",
    "schedule_followup": "Schedule follow-up or recheck work within the allowed day range.",
    "request_approval": "Queue a proposal version for human approval.",
    "end": "Request completion after checking all required work.",
    "submit_approved": "Submit an approved proposal through the mock submission gates.",
    "wait_until": "Advance the simulated calendar and process released evidence and due work.",
}


def tool_json_schemas(include_bench: bool = False) -> list[dict]:
    registry = {**TOOL_REGISTRY, **BENCH_TOOLS} if include_bench else TOOL_REGISTRY
    return [
        {
            "name": name,
            "description": TOOL_DESCRIPTIONS[name],
            "parameters": args.model_json_schema(),
        }
        for name, (args, _) in registry.items()
    ]
