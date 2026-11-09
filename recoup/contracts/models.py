"""Contracts from design/02 §3.2."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel

from .money import Money

Scalar = str | int | bool | None


class DocKind(str, Enum):
    invoice = "invoice"
    payment = "payment"
    remittance = "remittance"
    debit_memo = "debit_memo"
    po = "po"
    contract = "contract"
    amendment = "amendment"
    company_policy = "company_policy"
    insurance_policy = "insurance_policy"
    legal_authority = "legal_authority"
    bol = "bol"
    pod = "pod"
    tracking = "tracking"
    inspection = "inspection"
    photo = "photo"
    return_auth = "return_auth"
    email = "email"
    credit_memo = "credit_memo"
    statement = "statement"
    collection_note = "collection_note"
    other = "other"


class ExtractMethod(str, Enum):
    structured = "structured"
    text = "text"
    text_pdf = "text_pdf"
    ocr = "ocr"
    vision = "vision"
    none = "none"


class ExtractFailure(str, Enum):
    encrypted = "encrypted"
    corrupt = "corrupt"
    unsupported = "unsupported"
    ocr_unavailable = "ocr_unavailable"
    empty_text = "empty_text"


class FieldTrust(str, Enum):
    source = "source"
    model_extracted = "model_extracted"
    ocr = "ocr"
    vision = "vision"
    human_confirmed = "human_confirmed"


class Evidence(BaseModel):
    evidence_id: str
    case_id: str
    doc_ref: str
    version: int
    kind: DocKind
    title: str
    available_from: datetime
    content_sha256: str
    readable: bool
    method: ExtractMethod
    failure: ExtractFailure | None = None
    text: str = ""
    fields: dict[str, Scalar] = {}
    field_trust: dict[str, FieldTrust] = {}
    active: bool
    superseded_by: str | None = None


class FactRevision(BaseModel):
    fact_id: str
    case_id: str
    evidence_id: str
    key: str
    value: Scalar
    trust: FieldTrust
    citation: Citation | None
    supersedes_fact_id: str | None = None
    at: datetime
    by: str


class EffectiveFact(BaseModel):
    evidence_id: str
    doc_kind: DocKind
    doc_ref: str
    key: str
    value: Scalar
    trust: FieldTrust
    origin: Literal["source", "fact"]
    fact_id: str | None
    citation: Citation


class DocStatus(BaseModel):
    evidence_id: str
    doc_ref: str
    kind: DocKind
    readable: bool
    failure: ExtractFailure | None


class FactSet(BaseModel):
    case_id: str
    basis_hash: str
    facts: list[EffectiveFact]
    docs: list[DocStatus]
    buyer_senders: list[str] = []


class LineReasonRevision(BaseModel):
    case_id: str
    line_id: str
    reason: DeductionReason
    trust: FieldTrust
    citation: Citation | None
    at: datetime


class Citation(BaseModel):
    evidence_id: str
    locator: str
    quote: str


class DeductionReason(str, Enum):
    early_pay_discount = "early_pay_discount"
    pricing = "pricing"
    late_delivery = "late_delivery"
    damage = "damage"
    shortage = "shortage"
    returns = "returns"
    promo_rebate = "promo_rebate"
    unexplained_short_pay = "unexplained_short_pay"
    nonpayment = "nonpayment"


class DeductionLine(BaseModel):
    line_id: str
    reason: DeductionReason | None
    claimed: Money
    sku: str | None = None
    qty: int | None = None
    buyer_ref: str | None = None
    source_evidence_id: str | None = None
    reason_trust: FieldTrust = FieldTrust.source


class Verdict(str, Enum):
    valid = "valid"
    invalid = "invalid"
    partial = "partial"
    needs_info = "needs_info"


class Basis(str, Enum):
    proven = "proven"
    missing_evidence = "missing_evidence"
    contradiction = "contradiction"
    unsupported_terms = "unsupported_terms"
    untrusted_facts = "untrusted_facts"


class RuleFinding(BaseModel):
    line_id: str
    rule_id: str
    verdict: Verdict
    basis: Basis
    valid: Money | None
    disputed: Money | None
    missing: list[str] = []
    contradictions: list[tuple[Citation, Citation]] = []
    citations: list[Citation]
    note: str
    flags: list[str] = []


class LineDecision(BaseModel):
    line_id: str
    verdict: Verdict
    basis: Basis
    valid: Money | None
    disputed: Money | None
    citations: list[Citation]
    rationale: str


class Decision(BaseModel):
    decision_id: str
    case_id: str
    version: int
    evidence_set_hash: str
    lines: list[LineDecision]
    current: bool
    model_id: str
    llm_mode: Literal["fake", "replay", "live"]
    prompt_version: str
    created_at: datetime


class ProposalKind(str, Enum):
    dispute = "dispute"
    credit_memo = "credit_memo"
    info_request = "info_request"
    follow_up = "follow_up"
    insurer_notice = "insurer_notice"
    claim_package = "claim_package"
    correction = "correction"
    counteroffer = "counteroffer"


class Target(str, Enum):
    mock_buyer_portal = "mock_buyer_portal"
    mock_erp = "mock_erp"
    mock_email = "mock_email"
    mock_insurer = "mock_insurer"


KIND_TARGET: dict[ProposalKind, Target] = {
    ProposalKind.dispute: Target.mock_buyer_portal,
    ProposalKind.correction: Target.mock_buyer_portal,
    ProposalKind.counteroffer: Target.mock_buyer_portal,
    ProposalKind.credit_memo: Target.mock_erp,
    ProposalKind.info_request: Target.mock_email,
    ProposalKind.follow_up: Target.mock_email,
    ProposalKind.insurer_notice: Target.mock_insurer,
    ProposalKind.claim_package: Target.mock_insurer,
}


class ProposalStatus(str, Enum):
    proposed = "proposed"
    approved = "approved"
    rejected = "rejected"
    stale = "stale"
    cancelled = "cancelled"
    submitted_mock = "submitted_mock"


class LineAmount(BaseModel):
    line_id: str
    amount: Money


class Proposal(BaseModel):
    proposal_id: str
    business_key: str
    version: int
    case_id: str
    kind: ProposalKind
    target: Target
    recipient: str
    allocations: list[LineAmount] = []
    amount: Money | None
    draft_text: str
    draft_sha256: str
    citations: list[Citation]
    decision_id: str | None
    decision_version: int | None
    evidence_set_hash: str
    balance_basis: Money | None = None
    corrects_receipt_id: str | None = None
    offer_ref: str | None = None
    readiness_ids: list[str] = []
    status: ProposalStatus
    created_at: datetime
    created_by: Literal["agent", "human_edit", "scheduler"]


class Approval(BaseModel):
    approval_id: str
    proposal_id: str
    proposal_version: int
    offer_ref: str | None = None
    recipient: str
    amount: Money | None
    draft_sha256: str
    evidence_set_hash: str
    decision_version: int | None
    approver: str
    approved: bool
    reason: str = ""
    at: datetime
    void: bool = False
    void_reason: str = ""


class Receipt(BaseModel):
    receipt_id: str
    proposal_id: str
    proposal_version: int
    business_key: str
    idempotency_key: str
    target: Target
    amount: Money | None
    allocations: list[LineAmount] = []
    corrects_receipt_id: str | None = None
    offer_ref: str | None = None
    at: datetime
    label: str = "MOCK ACKNOWLEDGMENT — not sent to any real system"


class LedgerEntry(BaseModel):
    entry_id: str
    case_id: str
    kind: Literal["invoice", "payment", "credit_posted"]
    amount: Money
    line_id: str | None
    source: str
    at: datetime


ItemStatus = Literal["present", "missing", "defective", "restricted", "unknown"]


class ReadinessItem(BaseModel):
    item_id: str
    requirement: str
    status: ItemStatus
    satisfied_by: list[str] = []
    policy_citation: Citation | None = None
    note: str = ""


class Readiness(BaseModel):
    readiness_id: str
    case_id: str
    kind: Literal["dispute", "notice", "claim"]
    line_id: str | None = None
    status: Literal["ready", "not_ready", "not_applicable", "stale"]
    items: list[ReadinessItem]
    evidence_set_hash: str
    balance_basis: Money | None = None
    deadline: date | None = None
    deadline_citation: Citation | None = None


class CaseStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    needs_info = "needs_info"
    needs_human = "needs_human"
    proposed = "proposed"
    awaiting_reply = "awaiting_reply"
    closed = "closed"


class InsuranceStatus(str, Enum):
    none = "none"
    watching = "watching"
    notice_due = "notice_due"
    notice_submitted_mock = "notice_submitted_mock"
    claim_waiting = "claim_waiting"
    claim_ready = "claim_ready"
    claim_not_ready = "claim_not_ready"
    claim_submitted_mock = "claim_submitted_mock"


class DueWork(BaseModel):
    due_id: str
    case_id: str
    kind: Literal["follow_up", "notice_deadline", "claim_window", "recheck"]
    due_at: datetime
    basis: str
    status: Literal["pending", "done", "cancelled"] = "pending"
    idempotency_key: str


class DomainEvent(BaseModel):
    event_id: str
    case_id: str
    seq: int
    at: datetime
    type: Literal[
        "case_loaded",
        "evidence_added",
        "evidence_superseded",
        "duplicate_ignored",
        "receipt_issued",
        "ledger_changed",
        "reopened",
    ]
    ref: str
    processed: bool = False


class TraceEvent(BaseModel):
    run_id: str
    case_id: str
    step: int
    sim_time: datetime
    kind: Literal["tool_call", "model_call", "gate", "state", "stale", "event", "budget"]
    tool: str | None = None
    args: dict = {}
    result_summary: str = ""
    observation_sha256: str = ""
    model_id: str = ""
    llm_mode: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    controller: str = ""
    result: dict | None = None
    model_text: str = ""
    request: dict | None = None


class CaseView(BaseModel):
    case_id: str
    title: str
    buyer: str
    status: CaseStatus
    status_reason: str = ""
    insurance: InsuranceStatus
    sim_day: int
    sim_now: datetime
    invoice_total: Money
    open_balance: Money
    lines: list[DeductionLine]
    decision: Decision | None
    proposals: list[Proposal]
    receipts: list[Receipt]
    readiness: list[Readiness]
    due: list[DueWork]
    evidence: list[Evidence]
    provenance: Literal["synthetic"] = "synthetic"


class ActionAttempt(BaseModel):
    attempt_id: str
    case_id: str
    controller: str
    proposal_id: str
    version: int
    idempotency_key: str
    outcome: Literal["receipt", "idempotent_return", "gate_rejected", "transient_error"]
    receipt_id: str | None
    issues: list[GateIssue] = []
    at: datetime


class CaseHistory(BaseModel):
    case_id: str
    evidence_all: list[Evidence]
    facts: list[FactRevision]
    reasons: list[LineReasonRevision]
    decisions: list[Decision]
    proposals_all: list[Proposal]
    approvals: list[Approval]
    receipts: list[Receipt]
    attempts: list[ActionAttempt]
    ledger: list[LedgerEntry]
    events: list[DomainEvent]
    traces: list[TraceEvent]


class QuarantineRecord(BaseModel):
    case_id: str
    reason: str
    raw_bundle_json: str
    at: datetime


class LoadResult(BaseModel):
    case_id: str
    status: Literal["loaded", "quarantined"]
    reason: str = ""


class GateIssue(BaseModel):
    code: str
    message: str
    line_id: str | None = None


FactRevision.model_rebuild()
EffectiveFact.model_rebuild()
LineReasonRevision.model_rebuild()
ActionAttempt.model_rebuild()
CaseHistory.model_rebuild()
