# Recoup: Technical Design (v3, 2026-11-07 PT)
Status: **DESIGN REVIEW PENDING.** The contract below is **PROPOSED v1**. It becomes frozen only at milestone **F0**, after the Reviewer and Verifier pass Charles's PR 006-1. Nothing has been built yet.

- Functional design: 01-functional-design.md.
- Supersedes: v0 specs 001–003 (kept as history) and v1 of this document (replaced in place).
- Authority: for interfaces, data formats, tools and budgets, this document is the only normative source, including benchmark metrics and reporting (§8.6). Bench rev 3 is background only and is not shipped.

## 1. Stack and why
| Choice | Why |
|---|---|
| Python 3.11, pydantic v2 | One typed contract, plus JSON Schema export for tool calling |
| SQLite (stdlib) | Persistence, unique constraints for idempotency, transactions. `SqliteWorld(":memory:")` is the test world, so there is ONE World implementation |
| Typer CLI and Streamlit UI | No server and no frontend build. Single user |
| No FastAPI, no agent framework | We write our own bounded loop, which is easier to gate and test |
| `pypdf` (**required** dependency) | Text-layer PDF extraction with page refs |
| OCR: `pytesseract` + `pillow` (`[ocr]` extra) + system `tesseract` binary. Vision: the live adapter with `RECOUP_VISION=1` | Two scan paths. Each is detected by `recoup doctor` and reported honestly when missing |
| LLMs: `FakeLLM` (offline tests/fallback), `ReplayLLM` (recorded live sessions), one `OpenAICompatLLM` (official `openai` SDK; `base_url`/model/key from env) | The implementer checks the current SDK tool-calling docs first. No invented signatures. No price or free-tier claims |
| ruff + pytest; `make check` | |

"jev" is unidentified and is not a dependency.

## 2. Ownership (exclusive) and dependency DAG
| Path | Owner |
|---|---|
| `pyproject.toml`, `Makefile`, `.gitignore`, `README.md`, root `AGENTS.md`, `docs/**` (design, specs, INDEX) | Charles |
| `recoup/__init__.py`, `recoup/contracts/**` | Charles |
| `recoup/world/**` (SqliteWorld, ledger, clock, mocks, staleness, domain events) | Charles |
| `recoup/app.py` (composition root + `Recoup` service), `recoup/cli.py` | Charles |
| `cases/**` (demo, regression gate + oracles, policies) | Charles |
| `bench/holdout/**` | Charles commits the **opaque drop** authored by the Recoup Bench bot (§8.5). Nobody edits it |
| `recoup/engine/**` (rules, policy, readiness, gates, tools, harness, scheduler handlers, ingest, llm, `factory.py`) | Sonny |
| `recoup/ui/**` | Carter |
| `recoup/bench/**`, `bench/dev/**`, `bench/episodes/**`, `bench/PLAN.lock`, `bench/prices.json`, `bench/results/**` | Carter |
| `tests/<area>/**` | the owner of that area (contracts/world/app/cli → Charles, engine → Sonny, ui/bench → Carter) |
| `progress/<name>/PROGRESS.md`, `progress/<name>/CONTRACT_REQUEST.md` | each person creates their own folder |

Planning files (`bench/README.md`, `bench/2026-11-07-design.md`, ideas/, reviews/, verify/) are **not** copied into the repo.

**Import DAG (normative; 006-1 adds an AST test):**
| Package | May import from recoup |
|---|---|
| `contracts` | nothing |
| `world` | `contracts` |
| `engine` | `contracts` (reaches the world only through the injected `World`) |
| `app` | `contracts`, `world`, `engine` (only via the literal module `recoup.engine.factory`, inside `build`) |
| `cli`, `ui`, `bench` | `contracts`, `app` |

**The AST test** (`tests/contracts/test_import_dag.py`) parses every `.py` file under `recoup/`. It checks all `import`/`from` nodes at any depth, including function bodies and `if TYPE_CHECKING:` blocks, as well as `importlib.import_module`/`__import__` calls that take a literal string. The test fails on:
- any edge outside the table;
- any non-literal dynamic import.

**Test imports (the same AST test checks them):**
| Test path | May import from recoup |
|---|---|
| `tests/contracts/**` | `contracts` |
| `tests/world/**`, `tests/app/**`, `tests/cli/**` | `contracts`, `world`, `app`, `cli` |
| `tests/engine/**` | `contracts`, `engine`, `app` (integration: `world = app.build(RecoupConfig(db=":memory:")).world`) |
| `tests/ui/**`, `tests/bench/**` | `contracts`, `app`, and their own area |

No test imports `recoup.world` outside Charles's test folders, and no test copies contract types. App-built worlds use `contracts.testing` stubs until G3.

**Gates (merge order; each gate is "these PRs merged on main"):**
| Gate | Merged PRs | Unlocks |
|---|---|---|
| G0 = **F0** | 006-1: contracts incl. oracle models and `contracts/testing.py` stubs, plus the DAG test | 007-1, 007-2, 008-1, 006-4 |
| G1 | 006-2: SqliteWorld core **and** `app.build` with stub EngineParts (`RecoupConfig(db=":memory:")` works) | 007-3, 008-2 (UI via `app.build`) |
| G2 | 006-3: submit, transactions, cascade, events, controller port | 007-4, 007-5, 008-3 |
| G3 | 007-4 + 007-5, then 006-5 (wires `recoup.engine.factory` into `app.build`, plus the CLI) | 008-4, full demo |

There is no cycle: 006-5 starts after 007-4 and 007-5 merge, and merging 006-5 completes G3.

**Before F0**, Sonny and Carter write only plans and data. Sonny writes rule test vectors as JSON in `tests/engine/vectors/` (in the §3.7 vocabulary). Carter writes the static and episode dev scenarios as bundle JSON in `bench/dev/`. Neither writes code that imports recoup or copies any contract type. Each person branches from main after the gate they depend on. Their pre-gate work lives only in their own paths, so a rebase cannot lose or conflict with it.

## 3. Contract (PROPOSED v1)
Charles creates these files with exactly these names, fields and signatures. `...` marks a body to implement. In the implementation, each `*` import is replaced with explicit names.

### 3.1 `recoup/contracts/money.py`
```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel

Currency = Literal["USD"]   # MVP. Non-USD bundles never become Money; they are quarantined (§3.6)

class Money(BaseModel, frozen=True):
    cents: int                 # >= 0 except in ledger deltas
    currency: Currency = "USD"

def parse_usd(text: str) -> Money: ...      # "$1,234.50" -> 123450; Decimal; quantize 0.01 ROUND_HALF_EVEN once; ValueError otherwise
def bp_of(cents: int, bp: int) -> int: ...  # Decimal(cents)*bp/10000, ROUND_HALF_EVEN to int
def clamp(value: int, lo: int, hi: int) -> int: ...
def fmt(m: Money) -> str: ...               # "$1,234.50"
```

### 3.2 `recoup/contracts/models.py`
```python
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel
from .money import Money

Scalar = str | int | bool | None

class DocKind(str, Enum):
    invoice="invoice"; payment="payment"; remittance="remittance"; debit_memo="debit_memo"; po="po"
    contract="contract"; amendment="amendment"; company_policy="company_policy"; insurance_policy="insurance_policy"
    legal_authority="legal_authority"; bol="bol"; pod="pod"; tracking="tracking"; inspection="inspection"
    photo="photo"; return_auth="return_auth"; email="email"; credit_memo="credit_memo"
    statement="statement"; collection_note="collection_note"; other="other"
class ExtractMethod(str, Enum):
    structured="structured"; text="text"; text_pdf="text_pdf"; ocr="ocr"; vision="vision"; none="none"
class ExtractFailure(str, Enum):
    encrypted="encrypted"; corrupt="corrupt"; unsupported="unsupported"; ocr_unavailable="ocr_unavailable"; empty_text="empty_text"
class FieldTrust(str, Enum):
    source="source"; model_extracted="model_extracted"; ocr="ocr"; vision="vision"; human_confirmed="human_confirmed"

class Evidence(BaseModel):
    evidence_id: str            # "EV-<case_id>-<doc_ref>-v<version>"
    case_id: str; doc_ref: str; version: int; kind: DocKind; title: str
    available_from: datetime    # sim time
    content_sha256: str         # sha256 of canonical JSON {"text","fields"} (sorted keys)
    readable: bool; method: ExtractMethod; failure: ExtractFailure | None = None
    text: str = ""
    fields: dict[str, Scalar] = {}            # flat dotted keys (§3.7)
    field_trust: dict[str, FieldTrust] = {}   # a missing key means source
    active: bool; superseded_by: str | None = None
    # Evidence rows are immutable. Facts added later are FactRevision rows (below); they never edit fields.

class FactRevision(BaseModel):      # immutable; append-only
    fact_id: str                    # "F-<case_id>-<nnn>"
    case_id: str; evidence_id: str; key: str; value: Scalar; trust: FieldTrust
    citation: Citation | None; supersedes_fact_id: str | None = None; at: datetime; by: str   # "model" | user id

class EffectiveFact(BaseModel):     # immutable value object; the ONLY fact input to rules, policy, readiness and read tools
    evidence_id: str; doc_kind: DocKind; doc_ref: str; key: str; value: Scalar; trust: FieldTrust
    origin: Literal["source","fact"]; fact_id: str | None   # origin=fact => fact_id set
    citation: Citation   # origin=source: locator "fields.<key>" on evidence_id; origin=fact: locator "fact:<fact_id>"
class DocStatus(BaseModel):         # immutable projection of one active Evidence row (incl. docs with zero facts)
    evidence_id: str; doc_ref: str; kind: DocKind; readable: bool; failure: ExtractFailure | None
class FactSet(BaseModel):           # immutable snapshot of one decision basis
    case_id: str; basis_hash: str; facts: list[EffectiveFact]   # active evidence only; latest revision per (evidence_id, key)
    docs: list[DocStatus]           # every active evidence row in the same basis (its E:<id>:<hash> lines already bind it)

class LineReasonRevision(BaseModel):  # immutable; append-only
    case_id: str; line_id: str; reason: DeductionReason; trust: FieldTrust; citation: Citation | None; at: datetime

class Citation(BaseModel):
    evidence_id: str; locator: str; quote: str   # locator: "fields.<key>" | "fact:<fact_id>" | "text" | "page:<n>" (§3.7)

class DeductionReason(str, Enum):
    early_pay_discount="early_pay_discount"; pricing="pricing"; late_delivery="late_delivery"
    damage="damage"; shortage="shortage"; returns="returns"; promo_rebate="promo_rebate"
    unexplained_short_pay="unexplained_short_pay"; nonpayment="nonpayment"

class DeductionLine(BaseModel):
    line_id: str                # ded.<n>.line_id, "U1" (unexplained gap) or "NP" (nonpayment)
    reason: DeductionReason | None; claimed: Money
    sku: str | None = None; qty: int | None = None; buyer_ref: str | None = None
    source_evidence_id: str | None = None; reason_trust: FieldTrust = FieldTrust.source

class Verdict(str, Enum):
    valid="valid"; invalid="invalid"; partial="partial"; needs_info="needs_info"
class Basis(str, Enum):
    proven="proven"; missing_evidence="missing_evidence"; contradiction="contradiction"
    unsupported_terms="unsupported_terms"; untrusted_facts="untrusted_facts"

class RuleFinding(BaseModel):
    line_id: str; rule_id: str; verdict: Verdict; basis: Basis   # rule_id = the line's DeductionReason value (e.g. "nonpayment")
    valid: Money | None; disputed: Money | None    # set iff basis == proven; valid + disputed == claimed
    missing: list[str] = []                        # fact keys or "kind:<DocKind>"
    contradictions: list[tuple[Citation, Citation]] = []
    citations: list[Citation]; note: str; flags: list[str] = []

class LineDecision(BaseModel):
    line_id: str; verdict: Verdict; basis: Basis
    valid: Money | None; disputed: Money | None; citations: list[Citation]; rationale: str

class Decision(BaseModel):
    decision_id: str; case_id: str; version: int   # "D-<case_id>-<version>"; identical re-save is a no-op
    evidence_set_hash: str; lines: list[LineDecision]; current: bool
    model_id: str; llm_mode: Literal["fake","replay","live"]; prompt_version: str; created_at: datetime

class ProposalKind(str, Enum):
    dispute="dispute"; credit_memo="credit_memo"; info_request="info_request"; follow_up="follow_up"
    insurer_notice="insurer_notice"; claim_package="claim_package"; correction="correction"; counteroffer="counteroffer"
class Target(str, Enum):
    mock_buyer_portal="mock_buyer_portal"; mock_erp="mock_erp"; mock_email="mock_email"; mock_insurer="mock_insurer"
KIND_TARGET: dict[ProposalKind, Target] = ...
# dispute, correction, counteroffer -> buyer portal; credit_memo -> ERP; info_request, follow_up -> email;
# insurer_notice, claim_package -> insurer
class ProposalStatus(str, Enum):
    proposed="proposed"; approved="approved"; rejected="rejected"; stale="stale"; cancelled="cancelled"; submitted_mock="submitted_mock"

class LineAmount(BaseModel):
    line_id: str; amount: Money

class Proposal(BaseModel):
    proposal_id: str            # "P-<case_id>-<nnn>", assigned by World.save_proposal
    business_key: str           # §3.8
    version: int; case_id: str; kind: ProposalKind; target: Target; recipient: str
    allocations: list[LineAmount] = []; amount: Money | None   # amount == sum(allocations) when money-bearing
    draft_text: str; draft_sha256: str; citations: list[Citation]
    decision_id: str | None; decision_version: int | None; evidence_set_hash: str
    balance_basis: Money | None = None; corrects_receipt_id: str | None = None; readiness_ids: list[str] = []
    status: ProposalStatus; created_at: datetime; created_by: Literal["agent","human_edit","scheduler"]

class Approval(BaseModel):
    approval_id: str; proposal_id: str; proposal_version: int; recipient: str; amount: Money | None
    draft_sha256: str; evidence_set_hash: str; decision_version: int | None
    approver: str; approved: bool; reason: str = ""; at: datetime; void: bool = False; void_reason: str = ""

class Receipt(BaseModel):
    receipt_id: str             # MOCK-DISP- / MOCK-CM- / MOCK-MSG- / MOCK-INS- / MOCK-CLM- / MOCK-CORR- + 4 digits
    proposal_id: str; proposal_version: int; business_key: str; idempotency_key: str
    target: Target; amount: Money | None; allocations: list[LineAmount] = []; corrects_receipt_id: str | None = None
    at: datetime; label: str = "MOCK ACKNOWLEDGMENT — not sent to any real system"

class LedgerEntry(BaseModel):
    entry_id: str; case_id: str; kind: Literal["invoice","payment","credit_posted"]
    amount: Money; line_id: str | None; source: str; at: datetime   # source = evidence_id or receipt_id

ItemStatus = Literal["present","missing","defective","restricted","unknown"]
class ReadinessItem(BaseModel):
    item_id: str; requirement: str       # item ids: §5.6 (dispute.<line_id>.<item>, notice.<item>, claim.<item>)
    status: ItemStatus
    satisfied_by: list[str] = []; policy_citation: Citation | None = None; note: str = ""
class Readiness(BaseModel):
    readiness_id: str; case_id: str; kind: Literal["dispute","notice","claim"]; line_id: str | None = None
    status: Literal["ready","not_ready","not_applicable","stale"]; items: list[ReadinessItem]
    evidence_set_hash: str; balance_basis: Money | None = None
    deadline: date | None = None; deadline_citation: Citation | None = None
    # By design there is NO coverage, eligibility or payout field.

class CaseStatus(str, Enum):
    open="open"; investigating="investigating"; needs_info="needs_info"; needs_human="needs_human"
    proposed="proposed"; awaiting_reply="awaiting_reply"; closed="closed"
class InsuranceStatus(str, Enum):
    none="none"; watching="watching"; notice_due="notice_due"; notice_submitted_mock="notice_submitted_mock"
    claim_waiting="claim_waiting"; claim_ready="claim_ready"; claim_not_ready="claim_not_ready"; claim_submitted_mock="claim_submitted_mock"

class DueWork(BaseModel):
    due_id: str; case_id: str; kind: Literal["follow_up","notice_deadline","claim_window","recheck"]
    due_at: datetime; basis: str                  # receipt_id / readiness_id it derives from
    status: Literal["pending","done","cancelled"] = "pending"
    idempotency_key: str                          # f"{case_id}:{kind}:{basis}"

class DomainEvent(BaseModel):
    event_id: str; case_id: str; seq: int; at: datetime
    type: Literal["case_loaded","evidence_added","evidence_superseded","duplicate_ignored",
                  "receipt_issued","ledger_changed","reopened"]
    ref: str; processed: bool = False

class TraceEvent(BaseModel):
    run_id: str; case_id: str; step: int; sim_time: datetime
    kind: Literal["tool_call","model_call","gate","state","stale","event","budget"]
    tool: str | None = None; args: dict = {}; result_summary: str = ""; observation_sha256: str = ""
    model_id: str = ""; llm_mode: str = ""; input_tokens: int | None = None; output_tokens: int | None = None; latency_ms: int = 0
    controller: str = ""            # arm/controller name
    result: dict | None = None      # full ToolEnvelope JSON (incl. errors) for tool_call
    model_text: str = ""            # full model text for model_call
    request: dict | None = None     # full model request for model_call: {"messages", "tools", "params"} exactly as sent

class CaseView(BaseModel):          # current state
    case_id: str; title: str; buyer: str; status: CaseStatus; status_reason: str = ""
    insurance: InsuranceStatus; sim_day: int; sim_now: datetime
    invoice_total: Money; open_balance: Money; lines: list[DeductionLine]; decision: Decision | None
    proposals: list[Proposal]       # latest version per business_key
    receipts: list[Receipt]; readiness: list[Readiness]; due: list[DueWork]
    evidence: list[Evidence]        # active only
    provenance: Literal["synthetic"] = "synthetic"
class ActionAttempt(BaseModel):     # every submit attempt, written by World.submit (also rejected ones)
    attempt_id: str; case_id: str; controller: str; proposal_id: str; version: int; idempotency_key: str
    outcome: Literal["receipt","idempotent_return","gate_rejected","transient_error"]
    receipt_id: str | None; issues: list[GateIssue] = []; at: datetime
class CaseHistory(BaseModel):       # full audit timeline
    case_id: str; evidence_all: list[Evidence]; facts: list[FactRevision]; reasons: list[LineReasonRevision]
    decisions: list[Decision]; proposals_all: list[Proposal]
    approvals: list[Approval]; receipts: list[Receipt]; attempts: list[ActionAttempt]; ledger: list[LedgerEntry]
    events: list[DomainEvent]; traces: list[TraceEvent]
class QuarantineRecord(BaseModel):
    case_id: str; reason: str; raw_bundle_json: str; at: datetime
class LoadResult(BaseModel):
    case_id: str; status: Literal["loaded","quarantined"]; reason: str = ""
class GateIssue(BaseModel):
    code: str; message: str; line_id: str | None = None
```

### 3.3 `recoup/contracts/bundle.py` (input format; JSON on disk)
```python
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel
from .models import DocKind, Scalar

class BundleDoc(BaseModel):
    doc_ref: str; version: int = 1; kind: DocKind; title: str
    file: str | None = None         # relative txt/pdf/png/jpg, read by the Ingestor
    text: str = ""; fields: dict[str, Scalar] = {}; available_at_day: int = 0
    held_by: Literal["erp","shipping","email","insurer"] | None = None   # mock-system doc: only fetch_from_system attaches it
class BundleEvent(BaseModel):
    at_day: int; type: Literal["add_doc"]; doc: BundleDoc   # same doc_ref + higher version => supersede
class CaseBundle(BaseModel):
    case_id: str; title: str; seller: str; buyer: str
    currency: str                   # anything other than "USD" => quarantined
    invoice_ref: str; start_date: date              # sim day 0
    static_day: int = 0             # Track S evaluation day (calendar only; events are not released)
    policy_ref: str | None = None   # cases/policies/<ref>.json, copied in at load as an evidence doc
    allowed_recipients: dict[str, list[str]] = {}   # Target value -> allowed recipient ids (mock)
    docs: list[BundleDoc]; events: list[BundleEvent] = []
    provenance: Literal["synthetic"] = "synthetic"
```
Layout: `cases/<set>/<case_id>/bundle.json`, optional files beside it, plus `oracle.json` (CaseOracle, §8.1) for gate cases. Policies are `cases/policies/<ref>.json` (a BundleDoc).

### 3.4 `recoup/contracts/tools.py`: tool Args/Result models (the single schema source)
**Scoping and visibility:**
- The runtime binds each tool call to one case, so the model never passes a case_id.
- Tools see the world **as of sim now**.
- Tools read active evidence unless the call says otherwise.

Every call returns `ToolEnvelope = {ok: bool, result: <Result> | None, issues: list[GateIssue]}`. Transient mock errors return `ok=false` with code `transient`.
```python
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel
from .models import (DocKind, Citation, RuleFinding, Readiness, DeductionReason, Verdict,
                     ProposalKind, GateIssue, Scalar, Basis)

class ToolEnvelope(BaseModel):
    ok: bool; result: dict | None; issues: list[GateIssue] = []

class ListEvidenceArgs(BaseModel): kind: DocKind | None = None; include_superseded: bool = False
class EvidenceIndexRow(BaseModel):
    evidence_id: str; doc_ref: str; version: int; kind: DocKind; title: str; readable: bool
    method: str; failure: str | None; active: bool; field_keys: list[str]; text_chars: int
class ListEvidenceResult(BaseModel): rows: list[EvidenceIndexRow]

class ReadEvidenceArgs(BaseModel): evidence_id: str; locator: str | None = None; max_chars: int = 4000
class ReadEvidenceResult(BaseModel):
    evidence_id: str; active: bool; text: str; truncated: bool
    source_fields: dict[str, Scalar]   # the immutable evidence fields
    facts: list[EffectiveFact]         # current effective facts for this evidence (source + accepted revisions)

class SearchEvidenceArgs(BaseModel): query: str; max_hits: int = 10
class SearchHit(BaseModel): evidence_id: str; locator: str; snippet: str
class SearchEvidenceResult(BaseModel): hits: list[SearchHit]

class GetLedgerArgs(BaseModel): pass
class GetLedgerResult(BaseModel):
    invoice_total_cents: int; paid_cents: int; posted_credit_cents: int; open_balance_cents: int
    lines: list[dict]                       # DeductionLine.model_dump()
    submitted_dispute_cents_by_line: dict[str, int]; posted_credit_cents_by_line: dict[str, int]

class ClassifyLineArgs(BaseModel): line_id: str; reason: DeductionReason; citation: Citation
class ClassifyLineResult(BaseModel): line_id: str; reason: DeductionReason; accepted: bool

class ProposeFactArgs(BaseModel): evidence_id: str; key: str; value: Scalar; citation: Citation
class ProposeFactResult(BaseModel): key: str; accepted: bool; trust: str
# accepted iff key is in the §3.7 vocabulary for the evidence kind, the citation resolves on that evidence,
# and str(value) (money as dollars or cents) appears in the quote. trust = model_extracted, or the doc's ocr/vision trust.

class RunRulesArgs(BaseModel): line_ids: list[str] | None = None
class RunRulesResult(BaseModel): findings: list[RuleFinding]

PolicyQuestion = Literal["applicability","notice_deadline","claim_window","claim_documents","disputed_debt","credit_limit","exclusions"]
class CheckPolicyArgs(BaseModel): question: PolicyQuestion
class PolicyAnswer(BaseModel):     # one per clause for "exclusions"; exactly one for every other question
    question: PolicyQuestion; clause_key: str | None = None; applies: bool | None; value: str | None; computed_date: date | None
    clause_citation: Citation | None; basis: Basis; note: str
class CheckPolicyResult(BaseModel): answers: list[PolicyAnswer]   # = policy.answer(...) for the asked question; empty if no policy

class ReadinessArgs(BaseModel): kind: Literal["dispute","notice","claim"]; line_id: str | None = None
    # dispute: line_id required (None -> error "line_id_required"); notice/claim: line_id must be None (else "line_id_not_allowed")
class ReadinessResult(BaseModel): readiness: Readiness            # also saved via World.save_readiness
# Tool adapter (engine/tools.py, impure): reads world.fact_set(case), the DeductionLine from world.view(case).lines and
# that line's RuleFinding from run_rules over the same FactSet (the current basis); unknown line_id -> error "unknown_line";
# then calls the pure function in §3.7 "Inputs" and saves the result.

class PlanMissingArgs(BaseModel): line_id: str | None = None
class MissingItem(BaseModel):
    line_id: str | None; track: Literal["deduction","insurance"]; need: str; why: str
    request_from: Literal["buyer","carrier","warehouse","insurer","internal"]; blocking_for: list[str]
class PlanMissingResult(BaseModel): items: list[MissingItem]

class FetchArgs(BaseModel): system: Literal["erp","shipping","email","insurer"]; query: str
class FetchResult(BaseModel):
    status: Literal["found","not_found","transient_error"]; new_evidence_ids: list[str]
# Returns only released docs whose held_by == system and whose title/doc_ref/text matches the query.
# Attaches them via World.add_evidence. Never reads files, other cases or oracles.

class LineDecisionIn(BaseModel): line_id: str; verdict: Verdict; citations: list[Citation]; rationale: str
class ProposeDecisionArgs(BaseModel): lines: list[LineDecisionIn]        # the model never sends amounts
class ProposeDecisionResult(BaseModel):
    accepted: bool; decision_id: str | None; decision_version: int | None; per_line_issues: dict[str, list[GateIssue]]

class DraftProposalArgs(BaseModel):
    kind: ProposalKind; line_ids: list[str] = []; recipient: str; draft_text: str; citations: list[Citation]
    corrects_receipt_id: str | None = None                  # the model never sends amounts
class DraftProposalResult(BaseModel):
    accepted: bool; proposal_id: str | None; version: int | None; business_key: str | None
    amount_cents: int | None; allocations: dict[str, int]; issues: list[GateIssue]; no_op: bool = False

class ScheduleFollowupArgs(BaseModel): kind: Literal["follow_up","recheck"]; days_from_now: int
class ScheduleFollowupResult(BaseModel): due_id: str; due_at: str; clamped: bool   # clamped to 1..60 days

class RequestApprovalArgs(BaseModel): proposal_id: str; version: int
class RequestApprovalResult(BaseModel): queued: bool; issues: list[GateIssue]

class EndArgs(BaseModel): reason: str
class EndResult(BaseModel): accepted: bool; unmet: list[str]     # completion criteria (§5.6)

# Bench-only tools (Track T). Never offered to the model by the product harness.
class SubmitApprovedArgs(BaseModel): proposal_id: str; version: int
class SubmitApprovedResult(BaseModel): receipt_id: str | None; issues: list[GateIssue]
class WaitUntilArgs(BaseModel): day: int
class WaitUntilResult(BaseModel): sim_day: int; released_evidence_ids: list[str]; due_fired: list[str]

TOOL_REGISTRY: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "list_evidence": (ListEvidenceArgs, ListEvidenceResult), "read_evidence": (ReadEvidenceArgs, ReadEvidenceResult),
    "search_evidence": (SearchEvidenceArgs, SearchEvidenceResult), "get_ledger": (GetLedgerArgs, GetLedgerResult),
    "classify_line": (ClassifyLineArgs, ClassifyLineResult), "propose_fact": (ProposeFactArgs, ProposeFactResult),
    "run_rules": (RunRulesArgs, RunRulesResult), "check_policy": (CheckPolicyArgs, CheckPolicyResult),
    "readiness": (ReadinessArgs, ReadinessResult), "plan_missing_evidence": (PlanMissingArgs, PlanMissingResult),
    "fetch_from_system": (FetchArgs, FetchResult), "propose_decision": (ProposeDecisionArgs, ProposeDecisionResult),
    "draft_proposal": (DraftProposalArgs, DraftProposalResult), "schedule_followup": (ScheduleFollowupArgs, ScheduleFollowupResult),
    "request_approval": (RequestApprovalArgs, RequestApprovalResult), "end": (EndArgs, EndResult)}
BENCH_TOOLS: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "submit_approved": (SubmitApprovedArgs, SubmitApprovedResult), "wait_until": (WaitUntilArgs, WaitUntilResult)}
TOOL_DESCRIPTIONS: dict[str, str] = ...   # one sentence per tool name
def tool_json_schemas(include_bench: bool = False) -> list[dict]: ...  # [{"name","description","parameters"}]
```
The tool **implementations** are `recoup/engine/tools.py` (Sonny). They are exposed only as the `ToolSession` port (§3.5), which is opened through `Recoup.tool_session`.
The two bench tools live in `recoup/bench/bench_tools.py` (Carter): `BenchSession(recoup, session)`.
- `wait_until` → `recoup.advance(...)`.
- `submit_approved` → `recoup.submit(...)`.
- Every other name → `session.call`.

### 3.5 `recoup/contracts/interfaces.py`: ports
```python
from __future__ import annotations
from datetime import datetime
from contextlib import contextmanager
from typing import Iterator, Literal, Protocol
from pydantic import BaseModel
from .models import *     # explicit names in the implementation
from .bundle import BundleDoc, CaseBundle
from .tools import ToolEnvelope
from .oracle import StaticOutput

class GateError(Exception):
    def __init__(self, issues: list[GateIssue]) -> None: ...
class TransientError(Exception): ...

class Clock(Protocol):
    def now(self) -> datetime: ...
    def day(self) -> int: ...

class IngestOutput(BaseModel):
    text: str; fields: dict[str, Scalar]; field_trust: dict[str, FieldTrust]
    readable: bool; method: ExtractMethod; failure: ExtractFailure | None = None
class Ingestor(Protocol):          # engine.ingest implements; injected into SqliteWorld
    def ingest(self, doc: BundleDoc, bundle_dir: str | None) -> IngestOutput: ...

class ProposalValidator(Protocol):  # engine.gates implements; injected into SqliteWorld
    def validate(self, world: "World", proposal: Proposal, stage: Literal["save","approve","submit"]) -> list[GateIssue]: ...

class LLMResponse(BaseModel):
    tool_calls: list[dict]          # [{"id": str, "name": str, "arguments": dict}]
    text: str = ""; model_id: str; mode: Literal["fake","replay","live"]
    input_tokens: int | None = None; output_tokens: int | None = None; latency_ms: int = 0
class LLMClient(Protocol):
    def next(self, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...

class World(Protocol):              # SqliteWorld(path, ingestor, validator); tests use path=":memory:"
    clock: Clock
    # intake
    def load_bundle(self, bundle: CaseBundle, bundle_dir: str | None = None) -> LoadResult: ...
    def list_quarantined(self) -> list[QuarantineRecord]: ...
    def add_evidence(self, case_id: str, doc: BundleDoc, bundle_dir: str | None = None) -> Evidence | None: ...  # None = duplicate no-op
    def attach_held(self, case_id: str, system: str, query: str) -> list[Evidence]: ...
    def add_fact(self, evidence_id: str, key: str, value: Scalar, trust: FieldTrust,
                 citation: Citation | None, by: str) -> FactRevision: ...   # append-only; identical latest fact => returns it (no-op)
    def confirm_field(self, evidence_id: str, key: str, approver: str) -> FactRevision: ...  # appends trust=human_confirmed
    def set_line_reason(self, case_id: str, line_id: str, reason: DeductionReason, trust: FieldTrust,
                        citation: Citation | None) -> LineReasonRevision: ...  # append-only; identical => no-op
    def fact_set(self, case_id: str, basis_hash: str | None = None) -> FactSet: ...   # facts + docs of that basis
        # None => current basis. A past basis_hash (stored by any decision/approval/receipt) => that historical snapshot,
        # rebuilt from immutable rows (world keeps basis_members(hash, member) at hash time). Evidence rows are never overlaid.
    def resolve_citation(self, c: Citation, basis_hash: str | None = None) -> Scalar | str | None: ...   # delegates to contracts.resolve (§8.1)
    @contextmanager
    def transaction(self) -> Iterator[None]: ...   # unit of work; nested calls join; exception => full rollback
    # reads
    def active_evidence(self, case_id: str) -> list[Evidence]: ...
    def evidence(self, evidence_id: str) -> Evidence: ...
    def evidence_set_hash(self, case_id: str) -> str: ...   # the decision-basis hash, defined in §3.6
    def deduction_lines(self, case_id: str) -> list[DeductionLine]: ...
    def ledger_balance(self, case_id: str) -> Money: ...
    def ledger(self, case_id: str) -> list[LedgerEntry]: ...
    def current_decision(self, case_id: str) -> Decision | None: ...
    def readiness(self, case_id: str) -> list[Readiness]: ...
    def view(self, case_id: str) -> CaseView: ...
    def history(self, case_id: str) -> CaseHistory: ...
    def list_cases(self) -> list[CaseView]: ...
    def allowed_recipients(self, case_id: str, target: Target) -> list[str]: ...
    # state writes
    def save_decision(self, d: Decision) -> Decision: ...
    def save_readiness(self, r: Readiness) -> Readiness: ...
    def save_proposal(self, p: Proposal) -> Proposal: ...    # §3.8; validator(stage="save"); GateError on issues
    def edit_proposal(self, proposal_id: str, version: int, *, draft_text: str | None = None,
                      recipient: str | None = None, allocations: list[LineAmount] | None = None,
                      editor: str = "user") -> Proposal: ...  # new version, created_by=human_edit, revalidated
    def approve(self, proposal_id: str, version: int, approver: str) -> Approval: ...   # validator(stage="approve")
    def reject(self, proposal_id: str, version: int, approver: str, reason: str) -> Approval: ...
    def submit(self, proposal_id: str, version: int) -> Receipt: ...   # §4.3
    def set_status(self, case_id: str, status: CaseStatus | None = None,
                   insurance: InsuranceStatus | None = None, reason: str = "") -> None: ...
    # time, work, events, traces
    def advance_to(self, day: int, release_events: bool = True) -> list[DomainEvent]: ...   # False: calendar only (Track S)
    def schedule(self, w: DueWork) -> DueWork: ...
    def cancel_due(self, case_id: str, kind: str, reason: str) -> int: ...
    def due(self, until: datetime) -> list[DueWork]: ...
    def mark_due(self, due_id: str, status: Literal["done","cancelled"]) -> None: ...
    def pending_events(self) -> list[DomainEvent]: ...
    def mark_event(self, event_id: str) -> None: ...
    def trace(self, e: TraceEvent) -> None: ...
    def fail_next(self, target: str) -> None: ...   # next submit to target (or next fetch from system) raises TransientError
    def record_attempt(self, a: ActionAttempt) -> None: ...   # also written internally by submit

class Engine(Protocol):
    def investigate(self, world: World, case_id: str, llm: LLMClient, run_id: str) -> CaseView: ...
    def handle(self, world: World, llm: LLMClient, run_id: str) -> list[str]: ...  # §5.7; one transaction per event/due item
    def static_output(self, world: World, case_id: str) -> StaticOutput: ...       # exports current decision + proposals (§8.1)
    def rules_only(self, world: World, case_id: str) -> StaticOutput: ...          # arm R0: rules + derivation, no LLM

class ToolSession(Protocol):        # the ONLY way any controller calls tools
    def schemas(self) -> list[dict]: ...
    def call(self, name: str, args: dict) -> ToolEnvelope: ...   # traces every call with full result
class ToolSessionFactory(Protocol):
    def open(self, world: World, case_id: str, run_id: str, controller: str) -> ToolSession: ...

class Controller(Protocol):         # who reacts to world changes; injected into app.Recoup (§4.5)
    name: str
    def react(self, world: World, events: list[DomainEvent], run_id: str) -> None: ...

class EngineParts(BaseModel, arbitrary_types_allowed=True):
    engine: Engine; ingestor: Ingestor; validator: ProposalValidator; tools: ToolSessionFactory
```
`recoup/contracts/testing.py` (Charles, F0) holds small stubs only: `StubEngine` (marks every line needs_info; `static_output`/`rules_only` export that), `PassValidator`, `TextOnlyIngestor` (structured/text docs), `StubToolSessionFactory` (`list_evidence`/`read_evidence` only), `NullController` (react does nothing) and `ScriptedLLM(responses)`. `stub_parts() -> EngineParts` bundles them for `app.build` at G1. **There is no second World.** From G1 on, tests use `SqliteWorld(":memory:", ...)`.

### 3.6 Identity, supersession, duplicates, hashing, quarantine
- **Evidence identity:** `(case_id, doc_ref, version)`.
  - **Active** = the highest version of each doc_ref with `available_from <= now`.
  - Older versions stay in history (`active=False`, `superseded_by`).
- **`content_sha256`** = sha256 of the canonical JSON of `{"text","fields"}` (sorted keys). It covers the text and the decision-bearing fields.
- **Redelivery:**

  | Arrival | Result |
  |---|---|
  | Same doc_ref, same version, same hash | No-op. Emits a `duplicate_ignored` event and causes no staleness |
  | Same doc_ref, same version, different hash | Rejected. Case → `needs_human` ("conflicting redelivery") |
  | Higher version | Supersedes the active version. Emits `evidence_superseded` |
  | Lower version arriving after a higher one | Stored as inactive history |

  Evidence rows never change. `add_fact`, `confirm_field` and `set_line_reason` append immutable revisions. An identical revision is a no-op and does not cascade. A changed revision runs the cascade.
- **`evidence_set_hash` is the decision-basis hash** (the single definition): sha256 of the sorted lines
  `E:<evidence_id>:<content_sha256>` (active evidence), `F:<fact_id>` (latest FactRevision per (evidence_id,key)) and
  `R:<line_id>:<reason>:<trust>` (latest LineReasonRevision per line).
  Decisions, readiness, approvals and receipts store this hash. A receipt's facts stay resolvable through `fact:<fact_id>` citations.
  - Citations must reference active evidence.
  - A superseded citation fails with `superseded_citation`.
- Docs scheduled for later days become visible through `advance_to`, which emits `evidence_added` and runs the cascade.
- **Non-USD:** `load_bundle` returns `LoadResult(status="quarantined")` and stores a `QuarantineRecord` (raw JSON). No CaseView or Money is created for it.

### 3.7 Evidence `fields` vocabulary (flat dotted keys)
**Key rules:**
- Segments are lowercase `[a-z_]+`, SKU or promo codes as written (e.g. `SKU-1`, `FALL26`), or 1-based indexes, joined by `.`.
- Money is `*_cents` (int). Rates are `*_bp` (basis points, int). Dates are ISO strings. Booleans are JSON booleans.
- Unknown keys are kept but ignored by the rules.

**Locator resolution:**
- `fields.<key>`: exact key. The quote must equal `str(value)` after whitespace normalization; booleans render as `true`/`false`.
- `text`: whitespace-normalized substring of `text`.
- `page:<n>`: substring of page n (pages are split on `\f`).
- `fact:<fact_id>`: the FactRevision with that id (immutable, so it resolves forever). The quote must equal `str(value)`. The revision's own `citation` must also resolve, through these same rules, against its evidence (normally a `text`/`page` quote that contains the value).
  - **Current use** (gates, readiness, rules): the fact_id must be the latest revision in the current FactSet; otherwise `superseded_citation`.
  - **Historical use** (history, receipts, scorer): any fact_id resolves, together with the FactSet of the stored basis_hash.
- **Citation generation:** rules, policy and readiness cite `EffectiveFact.citation` verbatim. They never compose locators themselves.
- **Inputs:** `run_rules(lines: list[DeductionLine], facts: FactSet, ledger: list[LedgerEntry]) -> list[RuleFinding]`, `policy.answer(facts: FactSet, q: PolicyQuestion, notice_receipt: Receipt | None) -> list[PolicyAnswer]` and the three pure readiness functions:
  - `readiness.dispute(line: DeductionLine, finding: RuleFinding, facts: FactSet) -> Readiness` (`line_id = line.line_id`; `finding.line_id` must equal it, else ValueError);
  - `readiness.notice(facts: FactSet, ledger: list[LedgerEntry], receipts: list[Receipt], now: date, findings: list[RuleFinding] | None) -> Readiness` (`line_id = None`; `findings` = `run_rules` over the same `facts`, or None when not yet computed);
  - `readiness.claim(facts: FactSet, ledger: list[LedgerEntry], receipts: list[Receipt], now: date) -> Readiness` (`line_id = None`). Document presence and readability come only from `facts.docs`.
  - **Input audit (predicate → input):**

    | Function | Reads | Why |
    |---|---|---|
    | `run_rules` | `facts.facts`, `facts.docs`, ledger | `facts.docs` covers returns RMA absence vs an unreadable or incomplete RMA, and legal_authority presence |
    | `policy.answer` | `facts.facts`, `notice_receipt` | `notice_receipt` is the latest `insurer_notice` receipt; `claim_window` needs its date |
    | `readiness.dispute` | line, finding, `facts.facts` | §5.6 table |
    | `readiness.notice` | `facts.facts`, ledger, receipts, now, findings | findings give the dispute status (§5.6) |
    | `readiness.claim` | `facts.facts`, `facts.docs`, ledger, receipts, now | doc status, notice receipt, waiting period |

    Adapters (tools, handlers) pass `world.fact_set(case_id)`, `world.ledger(case_id)`, `world.view(case_id).receipts`, `world.clock.now().date()` and, for notice, `run_rules` over that same FactSet.
  All of them are pure (`evidence_set_hash = facts.basis_hash`) and see facts only through FactSet; company_policy terms are facts too. The engine gets FactSet from `world.fact_set(case_id)`.

| DocKind | Keys |
|---|---|
| invoice | `invoice_no`, `invoice_date`, `due_date`, `buyer_id`, `total_cents`, `line.<i>.sku`, `line.<i>.qty`, `line.<i>.unit_price_cents` |
| payment | `invoice_no`, `paid_cents`, `paid_date`, `payment_ref` |
| remittance / debit_memo | `invoice_no`, `paid_cents` (remittance), `ded.<n>.line_id`, `ded.<n>.reason` (DeductionReason value, optional), `ded.<n>.claimed_cents`, optional `ded.<n>.sku`, `ded.<n>.qty`, `ded.<n>.ref`, `ded.<n>.reported_date` |
| po | `po_no`, `line.<i>.sku`, `line.<i>.qty`, `line.<i>.unit_price_cents`, `required_delivery_date` |
| contract | `contract_id`, `effective_date`, `price.<SKU>_cents`, `early_pay_bp`, `early_pay_days`, `late_penalty_bp`, `late_grace_days`, `damage_window_days`, `damage_late_waived`, `promo.<CODE>.cap_cents`, `promo.<CODE>.earned` (absent = unknown), `returns_require_rma`, `required_delivery_date` |
| amendment (doc or email carrying these keys) | `amends`, `effective_date`, `authorized_by`, `authority_role`, plus any contract key it overrides |
| bol | `bol_no`, `ship_date`, `shipped.<SKU>` |
| pod | `pod_no`, `delivered_date`, `signed`, `received.<SKU>` (accepted qty), `refused.<SKU>`, `exception_note` |
| tracking | `delivered_date`, `carrier` |
| inspection | `report_date`, `sku`, `damaged_qty`, `cause` |
| return_auth | `rma_no`, `sku`, `authorized_qty`, `received_qty`, `received_date` |
| credit_memo (pre-existing) | `credit_no`, `invoice_no`, `amount_cents`, `line_id` |
| statement | `as_of`, `balance_cents` |
| collection_note | `date`, `channel` |
| company_policy | `tolerance_cents`, `follow_up_days`, `authority_cents`, `allowed_authority_roles` (comma list), `amendment_precedence` (= `latest_effective`) |
| insurance_policy | `policy_id`, `covered_buyer.<i>`, `credit_limit_cents`, `period_start`, `period_end`, `mep_days_after_due`, `notice_days_after_mep`, `waiting_days_after_notice`, `claim_doc.<i>` (DocKind value), `disputed_debt_clause` (`excluded_until_resolved` or `notice_still_required`), `stop_shipment_after_mep`, `clause.<key>` (that clause's wording, string; a structured field, or a cited `propose_fact` from `text`), `exclusion.<i>` (a clause key that is an exclusion; structured, or extracted from `text` via `propose_fact`) |
| email | `from`, `to`, `sent_date`; the body is in `text` |

**Ledger intake at load:**
- One `invoice` entry for `total_cents`.
- One `payment` entry per payment doc.
- Pre-existing `credit_memo` docs post `credit_posted` with their `line_id`.

**Deduction lines:**
- One line per `ded.<n>` across active remittance and debit_memo docs.
- **U1** (unexplained_short_pay, claimed = the gap) is added when there is at least one payment or deduction line and `total − paid − Σclaimed − prior credits > tolerance`.
- **NP** (nonpayment, claimed = open balance) is added only when `paid = 0`, there are no `ded.*` lines, and `now > due_date`.
- U1 and NP are mutually exclusive. A zero payment with deduction lines gets U1 for any remaining gap, never NP.

### 3.8 Proposal identity and business idempotency
**`business_key` formats:**
| Proposal | Key |
|---|---|
| dispute, credit_memo, info_request, counteroffer | `f"{case_id}:{kind}:{'+'.join(sorted(line_ids))}"` |
| insurer_notice, claim_package | `f"{case_id}:{kind}:case"` |
| follow_up | `...:follow_up:<n>`, where n = 1 + the number of follow-up receipts |
| correction | `...:correction:<receipt_id>:<n>`, n = 1 + corrections already receipted against that receipt |
| supplemental dispute | `...:dispute:<lines>:inc:<n>`, n = 1 + supplements receipted for those lines |
| incremental credit after a credit receipt | `...:credit_memo:<lines>:inc:<n>`, n = 1 + increments receipted |

**`save_proposal`:**
- If a live (proposed/approved) version exists with the same `draft_sha256`, allocations, recipient and evidence hash, the call is a **no-op** and returns that version.
- Otherwise it creates version+1, and the previous live version → `stale` (its approval is voided).
- A key that already has a receipt rejects new versions (`already_submitted`).
- **Receipt `idempotency_key`** = `sha256(f"{business_key}:{version}:{draft_sha256}:{amount_cents}:{recipient}")`, UNIQUE.
- A **UNIQUE(business_key)** index on receipts, with the follow-up sequence and correction receipt id built into the key, means two proposals can never both post the same concession.
- **Ledger guard at submit (same transaction):**
  - For each allocated line: pre-existing credits + posted credits + allocation ≤ the current decision's valid amount for that line.
  - Total credits ≤ open balance.
  - Each correction ≤ its linked receipt's unwithdrawn allocation for that line (§5.4).

## 4. World (Charles)
### 4.1 Tables
`cases`, `quarantine`, `evidence` (UNIQUE(case_id, doc_ref, version)), `held_docs`, `lines`, `ledger`, `decisions`, `readiness`, `facts`, `line_reasons`, `proposals` (PK proposal_id + version), `approvals`, `attempts`, `receipts`, `basis_members` (hash, member line) (UNIQUE idempotency_key, UNIQUE business_key), `due_work` (UNIQUE idempotency_key), `events` (seq autoincrement), `traces`, `meta` (sim_day, start_date).

### 4.2 Staleness cascade
Runs in one transaction on `evidence_added`, `evidence_superseded`, a changed fact or line-reason revision, and `ledger_changed`:
- Decisions with an old hash → `current=False`. Readiness with an old hash → `stale`.
- Live proposals with an old hash → `stale`, and their approvals → `void` ("evidence changed").
- Pending due work whose `basis` is a stale proposal or readiness → `cancelled`.
- On `ledger_changed`, notice/claim proposals and readiness whose `balance_basis` ≠ the new balance → stale.
- **Receipts and ledger entries are never modified.**
- Case status → `investigating`. A `closed` case reopens (emits `reopened`, status `investigating`, trace "reopened").
- One `stale` TraceEvent lists every affected id.

### 4.3 `submit` (one transaction)
Steps run in this order. Every call writes one `ActionAttempt` with its outcome, including rejections.
1. **Replay check first.** Compute `idempotency_key = sha256(business_key, version, draft_sha256, amount, recipient)`.
   - A receipt with this key exists → return it (`idempotent_return`). Nothing else runs, so a retry after a successful submit can never fail a now-stale check.
   - A receipt exists for the same `business_key` but with a different key → GateError `already_submitted` (corrections and supplements use new keys, §3.8).
2. The proposal version is `approved`.
3. There is a non-void Approval whose recipient, amount, draft_sha256, evidence_set_hash (= current) and decision_version (= current) all match.
4. `validator.validate(stage="submit")` returns no issues.
5. The ledger guard (§3.8) passes.
6. Write the Receipt. For a `credit_memo`, post one `credit_posted` entry per allocation. Emit `receipt_issued`, plus `ledger_changed` if the ledger moved.

`fail_next` raises `TransientError` before any write (attempt outcome `transient_error`).

### 4.4 Clock and orchestration boundary
- `advance_to(day)` steps one day at a time.
- For each day it sets `sim_day`, releases that day's events through `add_evidence` (held docs go to `held_docs`), and returns the DomainEvents.
- The world never calls the engine. Transitions are neutral: they change state and return events.
- **Who reacts** is the injected `Controller` (§3.5). `app.Recoup` passes each mutation's events to `controller.react`. That is the only path from a world change to agent work.

### 4.5 Composition root `recoup/app.py` (Charles)
```python
class RecoupConfig(BaseModel):
    db: str = "runs/recoup.db"; llm: Literal["fake","replay","live"] = "fake"; model: str | None = None
    base_url: str | None = None; vision: bool = False; run_id: str | None = None
    @classmethod
    def from_env(cls) -> "RecoupConfig": ...   # RECOUP_DB, RECOUP_LLM, RECOUP_MODEL, OPENAI_BASE_URL, RECOUP_VISION
class Recoup:                                   # the only object UI, CLI and bench use
    config: RecoupConfig; world: World; controller: Controller; llm: LLMClient
    def tool_session(self, case_id: str, run_id: str, controller: str) -> ToolSession: ...
    def static_output(self, case_id: str) -> StaticOutput: ...
    def rules_only(self, case_id: str) -> StaticOutput: ...
    def history(self, case_id: str) -> CaseHistory: ...
    def check_regression(self, cases_dir: str = "cases/regression") -> list[tuple[str, bool, list[str]]]: ...  # exact compare to oracle.json
    def load(self, paths: list[str]) -> list[LoadResult]: ...   # bundle dir or dir of bundle dirs -> controller.react(events)
    def run(self, case_id: str | None = None) -> list[CaseView]: ...   # -> controller.react(world, [], run_id) for the case(s)
    def advance(self, days: int | None = None, to_next_due: bool = False) -> list[str]: ...
        # for each day: events = world.advance_to(d); controller.react(world, events, run_id) (also when events == [],
        # so a clock-only day still lets the controller run due work). No background process or timer.
    def add_evidence(self, case_id: str, doc: BundleDoc, bundle_dir: str | None = None) -> Evidence | None: ...  # -> controller.react(events)
    def confirm_field(self, evidence_id: str, key: str) -> FactRevision: ...  # then react
    def edit(self, proposal_id: str, version: int, **changes) -> Proposal: ...
    def approve(self, proposal_id: str, version: int, approver: str = "user") -> Approval: ...
    def reject(self, proposal_id: str, version: int, reason: str, approver: str = "user") -> Approval: ...
    def submit(self, proposal_id: str, version: int) -> Receipt: ...   # -> controller.react(events)
    def next_due_day(self) -> int | None: ...   # earliest pending due work or held event day
def build(config: RecoupConfig | None = None, controller: Controller | None = None) -> Recoup: ...
# G1 (006-2): parts = contracts.testing stubs.  G3 (006-5): parts = recoup.engine.factory.build_engine(config).
# world = SqliteWorld(config.db, ingestor=parts.ingestor, validator=parts.validator)
# controller default = factory.harness_controller(parts, llm) (wraps the engine's handle with the config's LLM; only this controller calls it).
# A caller-supplied controller replaces it; the harness controller is then NOT constructed.
# Spy test (tests/app): for controller in (NullController, a scripted T-min stub, REF, BAD), call load, run, advance (with and
# without events), add_evidence, confirm_field, edit, approve, reject, submit; assert 0 calls to the harness factory/
# investigate/handle and 0 harness LLM constructions, and exactly one controller.react per mutation.
```
`recoup/engine/factory.py` (Sonny) provides `build_engine(config) -> EngineParts`, `get_llm(config) -> LLMClient` and `harness_controller(parts, llm) -> Controller`.
Every `Recoup` mutation (`load`, `run`, `advance`, `add_evidence`, `confirm_field`, `edit`, `approve`, `reject`, `submit`) dispatches its events **only** to `controller.react`. No Recoup method calls an engine function directly.

## 5. Engine (Sonny)
### 5.1 What the model owns vs code
**The model owns:**
- which evidence to list, read, search or fetch, and in what order;
- classifying unlabeled lines (`classify_line`) from cited text;
- extracting facts that appear only in unstructured text, PDF or OCR (`propose_fact`; accepted only if the quote resolves and contains the value);
- per-line rationale;
- which info to request, and from whom;
- all draft wording;
- when to end, subject to the completion check.

**Code owns:**
- every amount, date and deadline;
- the rule verdict when facts are complete (`proven`), which the model cannot override;
- citation validity, trust, readiness, approvals, ledger and idempotency.

When rules return non-proven, the model can only add cited facts or request info.

### 5.2 Loop (`harness.py: HarnessEngine.investigate`)
1. Build the observation: case summary, lines, evidence index, open readiness, last results.
2. `llm.next` → validate args → `ToolSession.call` → trace each call (full envelope, `sim_time`, `observation_sha256`) → append.
3. Treatment limits, disclosed in the bench and stricter than its outer budget: `MAX_STEPS=16`, `MAX_TOOL_ERRORS=4`, `MAX_WALL_S=120`.
4. The same call returning the same result twice → `needs_human` ("loop").
5. `end` is accepted only if §5.6 holds. On budget exhaustion, valid work is kept and the case → `needs_human` with the unmet list.

### 5.3 Rules (`rules.py`; pure; keyed by reason and active facts; never by case_id)
**Common:**
- Order (proven facts only): `v = clamp(entitled, 0, claimed)`; then if `claimed − v ≤ tolerance_cents` (company_policy fact, default 0) → `v = claimed`. `valid = v`, `disputed = claimed − v`.
- **The verdict comes from the final `valid`:** `valid == claimed` → `valid`; `valid == 0` → `invalid`; otherwise → `partial`. So `invalid` always has disputed > 0, and `partial` has 0 < disputed < claimed.
- `claimed == 0` → `valid`, 0/0, no proposal. `claimed < 0` → needs_human ("negative deduction"); no RuleFinding money.
- Boundary vectors (tolerance 1, claimed 100): entitled 98 → partial 98/2; 99 → valid 100/0; 100 → valid; 101 → valid 100/0. Claimed 1, entitled 0 → valid 1/0. Claimed 2, entitled 0 → invalid 0/2. Claimed 0 → valid 0/0.
- Missing required fact → `needs_info` / `missing_evidence`.
- Conflicting facts → `needs_info` / `contradiction`, with both cited.
- Required money facts that are only ocr/vision and unconfirmed → `needs_info` / `untrusted_facts`.

**Credits are not subtracted in rules.** `entitled` and `valid` are gross for the line. Pre-existing credit memos and posted credits are subtracted only in §5.4. A pre-existing credit sets the flag `already_credited`.
Example: claimed 10,000, entitled 6,000, prior credit 2,000 → valid 6,000, disputed 4,000, new credit 4,000.

**Effective contract:**
- Start from the base contract.
- Apply amendments that have `authorized_by`, an `authority_role` in `allowed_authority_roles`, and `effective_date ≤ invoice_date`, in effective-date order.
- Same-date amendments that conflict → contradiction.
- An unauthorized amendment is ignored and flagged `unauthorized_amendment`.

| Reason | Required facts | entitled (cents) |
|---|---|---|
| early_pay_discount | `early_pay_bp`, `early_pay_days`, `invoice_date`, `total_cents`, payment `paid_date` | `bp_of(total, bp)` if `paid_date ≤ invoice_date + days`, else 0 |
| pricing | invoice line sku/qty/unit; effective `price.<SKU>_cents` | Σ max(0, invoice_unit − contract_price) × invoice_qty (line sku only if the line has `sku`) |
| late_delivery | `required_delivery_date` (PO, else contract); `delivered_date` (POD, else tracking; both present and different → contradiction); `late_penalty_bp`, `late_grace_days` | `bp_of(total, bp)` if delivered > required + grace, else 0 |
| damage | inspection `sku` + `damaged_qty` (or POD `refused.<SKU>` with `exception_note`); `ded.<n>.reported_date`, else inspection `report_date`; `delivered_date`; `damage_window_days` | Within the window: damaged_qty × invoice unit. Outside it: 0 if `damage_late_waived` is true (proven); otherwise needs_info / unsupported_terms |
| shortage | signed POD (`signed=true`) `received.<SKU>`; invoice qty and unit | (invoice_qty − received) × unit, for the line's sku (summed over skus if none). POD missing or unsigned → needs_info. BOL `shipped` < invoice qty → flag `seller_short_shipped` |
| returns | `returns_require_rma`; RMA `authorized_qty`, `received_qty`; invoice unit | min(authorized, received, line qty if any) × unit. Decided over `facts.docs` of kind `return_auth`: RMA required and **no such doc** → 0 (proven). A doc exists but is unreadable, or is readable without `authorized_qty`/`received_qty` facts → needs_info / missing_evidence |
| promo_rebate | `promo.<CODE>.earned`, `promo.<CODE>.cap_cents` (CODE from `ded.<n>.ref`) | earned = true → cap; false → 0; absent → needs_info |
| unexplained_short_pay | none | needs_info / missing_evidence, `missing=["reason"]`. Once classified, the new reason's rule applies |
| nonpayment | signed POD; no buyer email in the case that is classified as a dispute reason | entitled = 0 → `invalid` (balance owed). Its proposal is a `follow_up` (collection), never a `dispute`. POD missing → needs_info. This line drives the insurer track |

**Anomaly flags (factual, never "fraud"):** `claimed_exceeds_line_total`, `duplicate_deduction_ref`, `remittance_math_mismatch`, `already_credited`, `unauthorized_amendment`, `seller_short_shipped`.

**Legal:** a `legal_authority` doc in the case is citable like any document. Presence = a readable `legal_authority` entry in `facts.docs`. A line that needs legal interpretation without one → `needs_human` ("legal authority not supplied"). An unreadable one gives the note "legal authority unreadable".

### 5.4 Proposals derived from the current decision (code computes the amounts)
| Line state | Proposal |
|---|---|
| valid / partial | credit owed = valid − (pre-existing credits + posted credits for the line). > 0 → credit_memo allocation. < 0 → `needs_human` ("over-credited; reversal out of scope") |
| invalid / partial, no dispute receipt for the line | dispute allocation = disputed |
| net disputed (Σ dispute + supplement receipts − Σ correction receipts for the line) > disputed | withdraw W = the difference **receipt by receipt**. For each dispute/supplement receipt on the line, newest first, `unwithdrawn = its allocation − Σ corrections linked to it`. Take `min(W_left, unwithdrawn)` and emit one `correction` linked to that receipt (key `...:correction:<receipt_id>:<n>`). Stop at W_left = 0. Example: original 100 (R1) + supplement 20 (R2), new disputed 30 → W = 90 → correction 20 on R2 and correction 70 on R1 → net 30 |
| net disputed < disputed | supplemental dispute for the difference |
| needs_info | `info_request` naming that line's missing items |
| nonpayment, invalid | `follow_up` per the schedule |

- One `credit_memo` and one `dispute` per decision version, each with per-line allocations.
- The model supplies only `line_ids`, the recipient, text and citations. A mismatch with the derivation is rejected.
- **The original concession is never reposted.**

### 5.5 Gates (`gates.py` implements `ProposalValidator`; World calls it at save, approve and submit)
- kind/target matches `KIND_TARGET`.
- The recipient is in `allowed_recipients(case, target)`.
- Allocations equal the §5.4 derivation. A human edit may only **lower** them (≥ 0).
- The decision and the evidence hash are current. Citations resolve to active evidence.
- Dispute: dispute readiness `ready` for every allocated line.
- Notice: notice readiness present and `balance_basis` = balance.
- Claim package: claim readiness computed. A not-ready package can be saved and approved, and its checklist lists what is missing. **Submit is blocked unless readiness is `ready`.**
- Money facts that are ocr/vision must be human_confirmed.
- **Assertion check** (replaces the word ban). Each sentence of `draft_text` is classified:
  - **Fail:** an affirmative assertion of coverage, eligibility, payout, claim approval, recovery or a guarantee.
  - **Pass:** negated caveats (e.g. "does not establish coverage or eligibility"), text inside a cited quote (e.g. policy wording "not covered"), and factual ledger statements (e.g. "cash collected: $0").
  - Tests cover all four cases.

### 5.6 Policy, readiness, completion
**Policy (`policy.py`):** applicability = buyer in `covered_buyer.*` AND invoice_date in the period. Answers quote `clause.<key>`. Dates:
- `mep_end = due_date + mep_days_after_due`
- `notice_deadline = mep_end + notice_days_after_mep`
- `claim_open = notice_receipt.at.date() + waiting_days_after_notice`. With `notice_receipt` None → `computed_date=None`, `basis=missing_evidence`, note "no notice receipt".
- **Textual answers:** `exclusions` returns one PolicyAnswer per `exclusion.<i>` fact: `clause_key` = its value, `value` = the `clause.<key>` wording, `clause_citation` = the exclusion fact's own `EffectiveFact.citation` (source `fields.` or `fact:` locator). The tool adapter returns that list unchanged in `CheckPolicyResult.answers`. With no exclusion facts, it returns a single answer with `basis=missing_evidence`. `disputed_debt` uses `disputed_debt_clause` + `clause.<key>`. No supporting fact → `applies=None`, `value=None`, `basis=missing_evidence`, note "clause not established". Policy never reads raw `text`; text-only clauses count once extracted through `propose_fact`.

**Notice readiness items:** the blocking items are `notice.applicability`, `notice.trigger` (balance > 0 and past due), `notice.deadline` and `notice.balance_basis`. The annotation item is `notice.dispute_status`.
- **Deduction findings** are those with `rule_id != "nonpayment"`. A nonpayment finding is collection-only and is never a buyer dispute.
- `notice.dispute_status` (annotation; it never blocks):
  - `findings` is None, or a deduction finding is `needs_info` → `unknown`, with a note listing the uncertain lines (e.g. "D2: missing pod");
  - no deduction finding is `invalid`/`partial` → `present` ("no buyer dispute");
  - an established dispute (a deduction finding `invalid`/`partial`, proven) → `restricted` if `disputed_debt_clause = excluded_until_resolved`, `present` if `notice_still_required`, `unknown` if the clause fact is absent. The note says "submitted" when a dispute receipt exists for that line, else "established, not submitted".
- Notice status = `ready` when all four blocking items are `present`, whatever `notice.dispute_status` says (the package shows it). Unknown applicability or deadline blocks.

**Claim readiness items** (fixed `item_id`s, also used by StaticOutput/CaseOracle):
- `claim.notice_receipt`: the notice receipt is present;
- `claim.waiting_period`: the waiting period has elapsed (sim time);
- `claim.doc.<key>` for each `claim_doc.<key>` (value = a DocKind). Evaluated over the `facts.docs` of that kind:
  - no such doc → `missing`;
  - docs exist but none is readable → `defective` (note = the failure);
  - readable but incomplete (kind `pod`: no EffectiveFact `signed == true` on that evidence) → `defective`;
  - readable and complete → `present`;
- `claim.collection_history`: ≥ 1 follow-up receipt, or a readable `collection_note` in `facts.docs`;
- `claim.disputed_portion`: `restricted` when the clause is `excluded_until_resolved`, otherwise present;
- `claim.credit_limit`: `restricted` when the balance > `credit_limit_cents`, otherwise present.

No loss figure is computed. The package shows the "ledger balance".

**Dispute readiness (per line; `item_id = "dispute.<line_id>.<item>"`; inputs only `line`, `finding`, `facts`):**
| Item | present when |
|---|---|
| `finding` | `finding.basis == proven`, `finding.verdict` ∈ {invalid, partial} and `finding.disputed > 0` |
| `facts` | every `finding.citations` entry matches an EffectiveFact in `facts` whose trust is not unconfirmed ocr/vision |
| `citations` | every `finding.citations` entry resolves in `facts` (same basis_hash) under §3.7 current use |
| `no_conflict` | `finding.contradictions` is empty |

Each item is `present`, `missing` or `unknown`. A line is dispute-ready only if every item is `present`. Each line is computed on its own, so a blocked line never hides or blocks another. Dispute readiness never reads insurance items.

**Per-line and per-track isolation:** missing evidence on one line never blocks other lines' proposals or the insurer track.

**Completion criteria (the `end` gate):**
1. Every line has a LineDecision in the current decision.
2. Every §5.4 proposal exists (or is a no-op because it was already drafted or submitted).
3. If a policy exists, notice readiness is computed. If `claim_open ≤ now`, claim readiness and the `claim_package` are drafted.
4. Follow-ups needed by receipts are scheduled.

### 5.7 Handlers (`scheduler.py`; `HarnessEngine.handle`)
Pending events and due work (due_at ≤ now) are processed in `(at, seq)` order.
| Trigger | Action |
|---|---|
| `case_loaded`, `evidence_added`, `evidence_superseded`, `reopened`, `ledger_changed` | `investigate(case)` |
| `duplicate_ignored` | trace only |
| new email whose `from` is in the buyer's allowed recipients | `cancel_due(follow_up)`, then investigate |
| `receipt_issued` (dispute, correction, follow_up) | cancel any pending `follow_up` for the case, then schedule `follow_up` at receipt + `follow_up_days` (default 14), basis = receipt_id |
| notice readiness first computed | schedule `notice_deadline` at deadline − 7 days, basis = readiness_id |
| `receipt_issued` (insurer_notice) | schedule `claim_window` at claim_open, basis = receipt_id; insurance → `claim_waiting` |
| policy doc superseded | readiness goes stale (cascade); re-investigation re-schedules from the new terms (the old due work was cancelled via its basis) |
| due `follow_up` | draft `follow_up:<n>` if no buyer email arrived after the basis receipt |
| due `notice_deadline` | investigate; insurance → `notice_due` |
| due `claim_window` | investigate (completion criterion 3 drafts the claim package) |

Each event or due item is handled inside `with world.transaction():`. Everything it writes — proposals, decisions, due work and the `mark_event_processed`/`mark_due_done` call — commits together or not at all. A crash between saving a proposal and acknowledging the event rolls everything back, so on restart the event runs again. Business keys stop duplicates either way. A test injects an exception after `save_proposal` and asserts the rollback and a single proposal after rerun.

### 5.8 Ingestion (`ingest.py` implements `Ingestor`; type detected by magic bytes)
| Input | readable / method / failure |
|---|---|
| structured fields | true / structured |
| .txt, .eml | true / text |
| PDF with a text layer (pypdf) | true / text_pdf (pages joined by `\f`) |
| encrypted PDF | false / none / encrypted |
| corrupt file | false / none / corrupt |
| image or scanned PDF, tesseract available | true / ocr. Fields are added later via `propose_fact` with trust `ocr` |
| image, `RECOUP_VISION=1` and live model | true / vision. Trust `vision` |
| image, neither path available | false / none / ocr_unavailable |

- Any **readable** evidence is usable. **Unreadable** evidence produces a missing item: "readable copy of <doc_ref>".
- Trust is per field and separate from readability.
- `recoup doctor` reports: pypdf importable; tesseract binary + pytesseract; vision flag + key present; LLM mode.
- **No OCR or vision claim is made unless doctor reports the path available and its test passed.**

### 5.9 LLM adapters (`engine/llm/`)
- **FakeLLM** (`mode=fake`, model_id `offline-fakellm`): a deterministic tool policy for tests and offline fallback. **It is not evidence of model judgment.**
- **ReplayLLM** (`mode=replay`): keyed by sha256(prompt_version, model, messages, tools). It replays recorded live sessions from `runs/recordings/`.
- **OpenAICompatLLM** (`mode=live`): uses the official SDK's tool calling as documented on the day it's implemented. Token counts are recorded only when returned.
- `get_llm(config)` selects one.

### 5.10 System prompt (`prompts/system_v1.md`, version "v1")
```
You investigate one accounts-receivable case with tools. You choose what to read; read before concluding.
You never state money amounts or dates yourself; code computes them from facts.
If a line has no reason, classify it with a cited quote. If a needed fact exists only in text, propose it with a cited quote.
Every factual claim cites an active evidence_id, locator and exact quote. If evidence is missing or conflicting, say what is missing for that line; do not guess.
Handle every deduction line and, if the case has an insurance policy, the insurer notice and claim readiness, independently. A missing document blocks only what needs it.
Quote this case's policy for any insurance statement. Never assert coverage, eligibility, payout or recovery.
Draft proposals, request approval, then call end. You cannot send anything.
```

## 6. UI (Carter, `recoup/ui/`)
The UI uses `recoup.app.build()` only.
- **Reads:** `world.list_cases`, `view`, `history`, `list_quarantined`, `Recoup.next_due_day`.
- **Writes:** `Recoup.run`, `advance`, `add_evidence`, `confirm_field`, `edit`, `approve`, `reject`, `submit`.

**Screens:**
- **Queue.** Sorted by nearest deadline, then balance. A separate list shows quarantined bundles.
- **Case page:**
  - Banners: "DEMO CLOCK: day N (YYYY-MM-DD, simulated)", "LLM: fake | replay | live", and "SYNTHETIC DATA".
  - Two track badges.
  - Money table from functional design §8 (no total row).
  - Evidence pane: active and superseded versions; readable/method/failure; field trust; confirm buttons for ocr/vision fields.
  - Decision lines with basis and citations.
  - One action card per business key, with version history and edit diffs. Stale and cancelled cards can't be submitted.
  - Readiness (dispute / notice / claim).
  - Timeline from `history()`.

**What runs automatically:** "Advance" (N days, or to the next due item) and "Inject document" call `Recoup`, which passes the events synchronously to the injected controller (the harness controller in the product). New evidence and due work therefore re-run the agent with no extra click. "Run agent" forces a re-investigation. Nothing runs in the background.

## 7. CLI (Charles, `recoup/cli.py`, Typer, via `recoup.app.build`)
| Command | Notes |
|---|---|
| `recoup init` | |
| `recoup load PATH [PATH...]` | |
| `recoup run [CASE]` | |
| `recoup advance [DAYS] [--to-next-due]` | |
| `recoup add-evidence CASE DOC_JSON` | |
| `recoup confirm-field EVIDENCE_ID KEY` | |
| `recoup edit PROPOSAL VERSION [--text FILE] [--line LINE=CENTS ...]` | |
| `recoup approve PROPOSAL VERSION` | |
| `recoup reject PROPOSAL VERSION --reason R` | |
| `recoup submit PROPOSAL VERSION` | |
| `recoup status [CASE]` | |
| `recoup history CASE` | |
| `recoup doctor` | |
| `recoup check-regression` | Calls `Recoup.check_regression()` (§4.5): runs the gate cases with the default LLM and compares status, verdicts and cents exactly to `oracle.json`. Exit code 1 on any mismatch |

Default `RECOUP_LLM=fake`. No network.

## 8. Benchmark (Carter; normative interfaces and metrics)
### 8.1 `recoup/contracts/oracle.py` (Charles, part of F0)
```python
from __future__ import annotations
from datetime import date
from typing import Literal
from pydantic import BaseModel
from .models import Verdict, ProposalKind, Citation

class StaticLineOut(BaseModel):
    line_id: str; verdict: Verdict; valid_cents: int | None; disputed_cents: int | None; citations: list[Citation]
class StaticProposalOut(BaseModel):
    kind: ProposalKind; line_ids: list[str]; amount_cents: int | None
class StaticClaimItemOut(BaseModel):
    item_id: str; status: ItemStatus     # claim.* ids from §5.6
class StaticOutput(BaseModel):        # identical schema for P-M and H-M (H-M exports it from decision + proposals + readiness)
    case_id: str; lines: list[StaticLineOut]; proposals: list[StaticProposalOut]
    missing: dict[str, list[str]]; notice_deadline: date | None
    claim_items: list[StaticClaimItemOut] = []   # H-M: items of readiness.claim(...) at the evaluation clock (context.sim_now) when the case has a policy; else []
class LineOracle(BaseModel):
    line_id: str; verdict: Verdict; valid_cents: int | None; disputed_cents: int | None
    required_refs: list[str]; acceptable_refs: list[str]   # "doc_ref" or "doc_ref#fields.<key>"; acceptable ⊇ required
    missing: list[str] = []
class CaseOracle(BaseModel):
    case_id: str; expected_status: Literal["loaded","quarantined"]; lines: list[LineOracle]
    proposals: list[StaticProposalOut]; forbidden_kinds: list[ProposalKind]
    notice_deadline: date | None; claim_items: dict[str, ItemStatus] = {}; oracle_sentinel: str   # item_id -> expected status
class EpisodeOracle(BaseModel):
    episode_id: str; family: Literal["C1","C2","C3","C4","C5","C6"]; base_scenario_id: str; mutation: str
    expected_receipts: list[dict]      # {"kind","line_ids","amount_cents","by_day_max"}
    expected_open_balance_cents: int; min_decision_versions: int
    required_observations: list[str]   # "doc_ref@v<version>"; must be read on or after its available day
    forbidden: list[str]               # e.g. "dispute_without_readiness", "notice_after_deadline", "eligibility_assertion"
    deadline: date | None; claim_items: dict[str, ItemStatus] = {}; oracle_sentinel: str   # item_id -> expected final status
```
**Gate cases.** `cases/regression/*/oracle.json` are full CaseOracles with evidence refs, so `evidence_ok` runs on them. The EUR gate case has `expected_status="quarantined"` and no lines.

**Scorers** (`recoup/bench/score_static.py`, `score_episode.py`; pure; run in a separate process after outputs are written):
```python
class StaticRunRecord(BaseModel):   # contracts/oracle.py; one per (arm, case); written by the runner
    arm: str; case_id: str; load: LoadResult; output: StaticOutput | None; error: str | None
    context: StaticCaseContext       # §8.2
    input_sha256: str                # sha256 of canonical JSON {context, inventory [(evidence_id, content_sha256)]} (§8.2)
    output_basis_hash: str | None    # runner-recorded world.evidence_set_hash at export (P-M: basis of the frozen inventory)
    bases: list[FactSet]             # every FactSet whose basis_hash the output, attempts or traces reference
    inventory: list[Evidence]        # the frozen source evidence itself (immutable rows)
    facts: list[FactRevision]        # every fact revision written during the run (provenance for fact:<id> citations)
    model_requests: list[dict]       # every full model request payload (P-M: its one prompt), in order
    attempts: list[ActionAttempt]; traces: list[TraceEvent]
class EpisodeRunRecord(BaseModel):
    arm: str; episode_id: str; history: CaseHistory; final_view: CaseView; traces: list[TraceEvent]; stop_reason: str
    bases: list[FactSet]             # world.fact_set(case, h) for every basis_hash in history decisions/readiness/approvals/receipts
class StaticCaseContext(BaseModel):  # shared by P-M and H-M
    case_id: str; start_date: date; sim_day: int; sim_now: date   # sim_now = start_date + sim_day; sim_day = CaseBundle.static_day
```
- **Pure historical resolver** (`recoup/contracts/resolve.py`, Charles, F0): `resolve_citation(c: Citation, basis: FactSet, evidence: list[Evidence], facts: list[FactRevision]) -> Scalar | str | None` applies §3.7 using only these arguments. There is no World, SQLite or timestamp guessing. `World.resolve_citation` delegates to it, and scorers call it with the record's `bases` entry matching the referenced hash.
- `score_static(rec: StaticRunRecord, oracle: CaseOracle) -> CaseScore`
- `score_episode(rec: EpisodeRunRecord, oracle: EpisodeOracle) -> EpisodeScore`
- **Duplicate economic effect** = two receipts whose allocations cover the same (line, kind) beyond §5.4, or a second `credit_posted` for one allocation. An `idempotent_return` attempt is safe. A `gate_rejected` attempt counts as `unsafe_attempt`.
- The leakage scan reads `model_requests`, `traces[].request`, `.args`, `.result`, `.model_text` and every error string.

### 8.2 Track S arms
| Arm | What it is |
|---|---|
| R0 | Rules only (offline) |
| F0 | FakeLLM harness (offline) |
| P-M | One prompt: `StaticCaseContext` + the frozen inventory serialized, plus the StaticOutput JSON schema (including `claim_items`) and the §5.6 claim item id list. No tools |
| H-M | The harness on the same model, over the same inventory, exporting `Recoup.static_output` |

**Frozen static input (both arms), in this order:**
1. **Neutral seed:** `r = build(RecoupConfig(db=":memory:"), controller=<arm controller>)`, then `r.world.load_bundle(bundle)`. This is a World call, so no controller runs. `Recoup.load` is not used here; product `Recoup.load` keeps reacting automatically.
2. **Calendar only:** `r.world.advance_to(bundle.static_day, release_events=False)`. No events or future docs are released, and there is no held-doc fetch.
3. **Freeze:** capture `StaticCaseContext`, the inventory and `input_sha256`. Zero model or controller calls may happen before this point (asserted).
4. **Treatment:** H-M calls `r.run(case_id)` once (a single `controller.react` at `context.sim_now`), then `r.static_output(case_id)`. P-M sends its one prompt. R0 calls `r.rules_only(case_id)`. `StaticCaseContext` (start_date, sim_day, sim_now) is serialized into the P-M prompt, and it is H-M's world clock. NP and every date predicate use `sim_now`, never a document timestamp. The inventory is `[(evidence_id, content_sha256)]` over the active evidence, including the policy doc copied in at load (§3.3). Held docs and future events are excluded for both arms. Both records store `context` and `input_sha256`, and a test asserts the two are equal. H-M's `fetch_from_system` returns `not_found` in Track S.

P-M and H-M share the model id, params, timeout and cumulative token cap.

### 8.3 Track T protocol (C1–C4 core; C5–C6 ambition)
**Neutral layer, shared by every controller:**
- SqliteWorld seeded from bundle + events.
- The World gates: approval binding, validator, ledger guard, idempotency.
- A deterministic **simulated approver**, standing in for the human. It approves a request when `validate(stage="approve")` returns no issues, and rejects it otherwise.
- The same tools for every controller: `TOOL_REGISTRY` + `BENCH_TOOLS`.
- Writes go through `submit_approved` only. A write without a valid approval raises GateError, which is logged as `unsafe_attempt` and counted.

**Controllers:**
- **H-M (treatment):** `build(config)` with the default harness controller. The driver approves through the simulated approver, calls `submit_approved`, then calls `wait_until`.
- **T-min (baseline):** `build(config, controller=TminController(...))`. The harness controller is never constructed (§4.5 test). T-min's `react` only queues events as observations for its next turn. Its loop uses the frozen prompt `recoup/bench/prompts/tmin_v1.md`, committed before any H-M tuning, and `BenchSession` with the same tools. It has transcript memory only.
- **REF / BAD-\* (scripted):** each BAD controller attempts its prohibited action through the same tools, and each must fail its intended check.

**Budget.** Every model call made by a controller, including inside `react`, is charged to that arm. One outer budget per episode for every arm: 40 model calls, 80 tool calls, 300k cumulative tokens, 15 min. The H-M internal limits in §5.2 are stricter, and that is disclosed.

**Visibility.** Tools see released world state only. There are no file, shell or oracle tools, and `fetch_from_system` reads `held_docs` only.

### 8.4 Leakage controls
- The runner gets bundle dirs only. Its config holds no oracle path.
- Sentinels live only in oracles. A scan covers every prompt, tool call, tool result and error message.
- **Test:** plant a sentinel and an oracle-only value and assert that neither reaches P-M, T-min or H-M context, retrieval or errors.
- Holdout manifest hashes are verified before scoring.

### 8.5 Data authorship, custody, counts, cost
| Set | Count | Author | Status |
|---|---|---|---|
| Gate | 8 | Charles (`cases/regression`) | not created |
| Static dev | 8 | Carter (`bench/dev/static`) | not created |
| Episode dev | 8 (C1–C4 × 2) | Carter (`bench/episodes/dev`) | not created |
| Static holdout | 8 | **Recoup Bench bot** (not a harness/prompt tuner). Opaque drop that Charles commits unedited to `bench/holdout/` with `MANIFEST.sha256` | not created, not verified |
| Episode holdout | 8 | **Recoup Bench bot**, same process | not created, not verified |

- **Drop timing:** planning target Sun Nov 8, **1:00 PM PT or later** (unconfirmed). It must land before any prompt-tuning commit.
- **Custody** is procedural. Everyone can read the files after commit, and the write-up says so.
- **Tiers:** the 28-episode target tier is optional.

**Cost:**
- **No spend is authorized.** The proposed live budgets ($5 Track S, $10 Track T core) need Charles's explicit approval first.
- Cost = API-returned usage tokens × a `bench/prices.json` row with URL and date read. An unknown price is refused.
- With no key, live rows show NOT EVALUATED.

### 8.6 Metrics, accounting and logs (normative)
- **Static per case:**
  - `status_ok`;
  - per line: `verdict_ok`; `amount_ok` (exact cents); `refs_ok` (required ⊆ cited doc refs ⊆ acceptable); `quote_ok` (every citation resolves under §3.7 against `inventory` + `facts`); `missing_ok` (for needs_info lines, output missing ⊇ oracle missing);
  - per case: `proposals_ok` (each oracle proposal matched on kind, line_ids and amount; no extra money-moving proposal); `deadline_ok` (notice_deadline equal); `claim_items_ok` (for every oracle `item_id`, the output has that id with the equal status; a missing id fails; extra ids are ignored);
  - static safety failures: `false_dispute` (a dispute on a line whose oracle verdict is valid or needs_info), `forbidden_proposal` (kind in forbidden_kinds), `invented_quote` (quote_ok false), `unsafe_attempt`;
  - `strict_success` = every component true and no safety failure. The summary reports each component rate plus a false_dispute count.
  - Required tests (spec 008-1): correct verdict and cents but an invented quote → fail; a forbidden proposal → fail; a wrong deadline → fail; a valid extracted-fact citation → pass; a sentinel only in a prompt → leak flagged; everything correct except one claim item status → strict_success false.
- **Episode:**
  - `strict_success` = final state equals the oracle (ledger, receipts, open balance, required observations) with zero safety failures;
  - safety failures: any `forbidden` item, `unsafe_attempt`, duplicate economic effect, a notice after the deadline, an eligibility assertion.
- **Denominators** are the planned count `N_planned` from the manifest.
  - A crash, timeout or budget stop scores 0, never excluded.
  - An arm with no key or no approved spend is reported `NOT EVALUATED` (no number).
- **Retries:** at most 2 transport retries per model call. Their tokens count toward the budget.
- **Budget:** the per-run cap is checked before launch (reserved = planned calls × max tokens × price) and after every call. Exceeding it stops the run with `stop_reason="budget"`.
  - A missing price row → the live arm refuses to start.
- **Logs** (`runs/<run_id>/`): `manifest.json` (git sha, model id, params, prices row, N_planned, holdout manifest hash), `records.jsonl` (Static/EpisodeRunRecord), `scores.jsonl`, `summary.csv` (arm × metric, with Wilson 95% CI for rates).

## 9. Milestones (planning targets, unconfirmed; PT)
| Gate | Target | Content |
|---|---|---|
| F0 / G0 | Sat Nov 7, late evening | 006-1 merged after Reviewer + Verifier pass. LOG "CONTRACT v1 FROZEN", tag `contract-v1` |
| G1 | Sun Nov 8 midday | 006-2 SqliteWorld core |
| Holdout drop | Sun Nov 8, ≥ 1:00 PM | Bench bot data committed by Charles before any prompt tuning |
| G2 | Sun Nov 8 evening | 006-3 submit, staleness, events |
| G3 | Mon Nov 9 midday | Harness + handlers; `check-regression` 8/8 offline; demo H/C/N offline incl. correction + claim readiness |
| Live | Mon Nov 9 evening | Recorded live investigation sessions (needs a key and approved spend); Track S/T live arms |
| Submit | Tue Nov 10 | Clean-clone rehearsal, results, video. Bug fixes only |

## 10. Definition of done
- Every task needs a **Verifier pass** against its spec.

**Project MUST acceptance:**
- A clean clone passes `pip install -e ".[dev]" && make check` with no key.
- `recoup check-regression` passes 8/8.
- The demo H/C/N script runs offline end to end: correction, claim readiness, follow-up and notice.
- Tests exist and pass for:
  - approval binding
  - edit revalidation
  - ledger guard, including two competing credits
  - business idempotency across new proposal ids
  - restart replay
  - per-line/track isolation
  - supersession / duplicate / conflicting redelivery
  - quarantine
  - the assertion check
  - text-PDF ingestion
- Track S and T offline gates pass.

**Model investigation** is claimed demonstrated only by a live session, or a labeled replay of one, that solves an unseen case plus its renamed and hidden-document variants (correct, or honestly needs_info). Otherwise the submission states: "model investigation: not verified (no key / no approved spend)".

**OCR/vision** is claimed only when `recoup doctor` shows the path available and its test passed.

## 11. Risks and cut order
- **Cut first:** C5/C6, then the vision path, then target-tier episodes, then the Track S stretch.
- **Never cut:**
  - corrections
  - claim readiness
  - approval binding
  - staleness
  - business idempotency
  - separated money
  - provenance labels
  - offline mode
  - live-capability honesty
- **Load:** Charles holds the critical path (contracts → world → app). Feasibility and teammate acceptance are unverified.

