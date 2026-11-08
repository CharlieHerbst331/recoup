# Recoup: Functional Design (v2, 2026-11-07 4:30 PM PT)
Status: **DESIGN REVIEW PENDING.** Nothing has been built. v2 replaces v1 in place after the Reviewer and Verifier findings (resolution map: design/03-review-resolution.md). This document supersedes the v0 plan (specs 001–003, which stay in the repo as history) and design/00-DRAFT-scope-skeleton.md.
Owner: Recoup Lead. Companion doc: design/02-technical-design.md.

**Inputs synthesized here:**
- round1.docx (our application)
- Sonny's ChatGPT conversation "Recoup Data Architecture" (https://chatgpt.com/share/6aefb740-15c4-83e8-b787-ad15d2ff4102), with categories A–E
- Ideator scope review plus its v2 addendum
- Agent Engineering harness advice, rev 2
- Recoup Bench design, rev 3 (background; design/02 §8 is normative)
- ideas/2026-11-03-*

**Source caveat.** Sonny's chat is assistant-generated. Its citations are not verified legal or insurance advice. Every policy, legal or deadline rule in Recoup is either (a) a **synthetic fixture fact** written into a case's own documents, or (b) a statement tied to one named public source and labeled "one example insurer, not universal". Recoup never applies a universal rule.

## 1. Product in one paragraph
Recoup is a single-user **AR case workbench**. An invoice that was short-paid, deducted or left overdue becomes a case. An agent investigates the case by choosing which documents and tools to consult. It decides, per deduction line, what to fight, what to concede and what it cannot decide yet. Then it drafts the dispute, credit memo, information request or follow-up.

When the invoice is insured, the agent runs a parallel insurer track. It computes the notice deadline from the case's own policy document, and it builds a claim package with a readiness checklist. That checklist never says "eligible" or "covered". The case keeps living over simulated time:
- replies and new documents trigger reconsideration;
- stale approvals are voided;
- follow-ups fire on schedule.

A human approves every step that leaves the company or changes the books. All external systems are **mocks**. Cash collected is always **$0** in the demo.

## 2. User and job
- **User:** an AR or deductions specialist at a supplier (the person Sonny's chat calls "the finance guy" or the supply-chain manager). The prototype is single-user, with no auth.
- **The job:** "For each problem invoice, tell me what happened, what is owed, what to fight vs concede, and what is due when. Draft it, cite it, and let me approve."

## 3. Why a case workbench, not a CRM
Charles's "CRM for invoices" idea is right about one thing: people work a queue of records. We keep three CRM-like surfaces: a **queue**, a **case record** and an **activity timeline**. We drop contacts, pipeline, multi-user, search and settings.

The unit of work is a **problem on an invoice** (a deduction line or an insurer obligation), not a customer record. The main screen shows the agent's **judgment**:

evidence → per-line verdict → proposed action → approve / edit / reject → mock receipt → audit.

A CRM displays records. A workbench makes the AI's reasoning load-bearing and checkable.

## 4. Scope tiers
- **MUST:** demoable for the Nov 10 submission and on the critical path.
- **SHOULD:** built after the MUST items pass.
- **AMBITION:** built after the SHOULD items.
- **ROADMAP:** pitch only. Never shown as implemented.

A MUST item that isn't built gets reported as **not implemented**. It is never replaced by a scripted stand-in.

| Capability | Tier |
|---|---|
| Case bundle intake: structured JSON, text docs and **text-layer PDF** (pypdf, a required dependency). Versioned evidence with hashes; supersession and duplicate rules | MUST |
| Model-chosen investigation over typed tools. Covers line classification and fact extraction from unstructured text, with validated quotes | MUST (needs a live model for proof, see §11) |
| Rules for all 9 of Sonny's deduction types: finite supported terms, integer USD cents, `needs_info` on missing, contradictory or unauthorized facts | MUST |
| Per-line verdict with basis (proven / missing / contradiction / unsupported terms / untrusted facts) and checked citations | MUST |
| Proposals derived by code: dispute, credit memo, info request, follow-up, insurer notice, **claim package**, **correction** | MUST |
| Scoped approval (binds recipient, amount, draft, evidence set, decision version). An edit creates a new version and is revalidated at save, approve and submit | MUST |
| Mock submission with an idempotent `MOCK-…` receipt. Business-level idempotency, so the same concession can't post twice. A posted credit reduces the mock ledger | MUST |
| New evidence makes affected items STALE: approvals void, unsent work cancelled, receipts kept. Changes after a send become a correction or an incremental credit | MUST |
| Labeled simulated clock. Events and due work processed automatically on advance. Follow-up after buyer silence; notice deadline; claim window | MUST |
| Insurer notice readiness and draft, using ≥ 2 contrasting synthetic policies | MUST |
| **Claim package with readiness checklist** (present / missing / defective / restricted, with policy citations). Submit allowed only when ready | MUST |
| Unexplained short pay → request explanation. No dispute | MUST |
| Non-USD bundle → quarantined, with the reason shown | MUST |
| Scan/image path: local OCR (tesseract) **or** a vision model behind a key, with OCR/vision fields untrusted until a human confirms. `recoup doctor` reports what is available; anything missing is shown honestly | SHOULD (OCR), AMBITION (vision) |
| Anomaly flags with cited facts. Never a fraud accusation | SHOULD |
| Legal questions: cite a legal-authority document supplied with the case, otherwise escalate. No general law engine | MUST (escalation), ROADMAP (corpus) |
| Multi-invoice remittance allocation (C5) | AMBITION |
| Counteroffer within configured authority; human approval required (C6) | AMBITION |
| Benchmark: offline gates; Track S (static, same model); Track T (episodes C1–C4, same tools) | MUST (offline gates and harness); live arms need a key and approved spend |
| Real ERP, email, portal or insurer connectors; real sends; auto-approve; claim loss calculation; real insurer filing; LoRA; routing; multi-currency; multi-user | ROADMAP |

## 5. Source-to-scope coverage matrix (Sonny categories A–E)
Legend:
- **M** = must
- **S** = should
- **A** = ambition
- **Mock** = simulated system
- **D** = deferred to the roadmap (named, never hidden)

Fixture facts are synthetic.

### A. Persistent company data
| Sonny item | Recoup handling | Tier |
|---|---|---|
| Accounting / ERP (invoices, payments, balances, credit memos, customers, due dates) | Mock ERP ledger in SQLite, seeded from each case bundle | M / Mock |
| Customer contracts (prices, terms, discounts, delivery, returns, penalties) | `contract` documents with clause ids; rules read the structured fields | M |
| Company policies (tolerances, dispute procedures, write-off, authorization limits) | `company_policy` document per bundle: deduction tolerance, authority limit for counteroffers | M (tolerance), A (authority/negotiation) |
| Trade credit insurance policies | ≥2 synthetic `insurance_policy` documents with explicit buyer applicability, credit limit, exclusions, MEP, notice window, waiting period, claim document list and a disputed-debt clause | M |
| Legal / regulatory references | Only through a supplied `legal_authority` document. Otherwise escalate. No general law engine | M (escalate) / D (corpus) |
| Customer records | Buyer name and id inside the bundle; prior disputes as email or notes | M (minimal) |
| Product / order records | Invoice and PO line items with SKU, qty, unit price in cents | M |

### B. Transaction-specific data
| Item | Handling | Tier |
|---|---|---|
| Invoice | doc kind `invoice` | M |
| Payment / bank record | doc kind `payment`; posted to the mock ledger | M |
| Remittance advice | doc kind `remittance` with deduction lines and reason codes | M |
| Debit memo | doc kind `debit_memo` | M |
| PO | doc kind `po` | M |
| BOL / POD / tracking | kinds `bol`, `pod`, `tracking` | M |
| Damage / shortage evidence (photos, inspection, carrier report, RMA) | `inspection`, `return_auth` as text; `photo` as image | M (text) / A (image) |
| Emails | kind `email`; buyer replies arrive as timed events | M |
| Credits / returns / prior adjustments | `credit_memo` docs plus ledger entries | M |
| Insurance claim information | Derived: ledger balance, collection history from follow-up receipts/notes | M |
| Short pay without memo or remittance | Detected from payment < invoice with no explanation → `unexplained_short_pay` → request info | M |

### C. External systems and action targets (all Mock)
| System | Read | Write (mock, approval-gated) | Tier |
|---|---|---|---|
| ERP | ledger, docs | post credit memo (reduces balance), status | M |
| Bank | payments | none | M (read) |
| Email | inbox events | outbox: dispute letters, info requests, follow-ups | M |
| Shipping | tracking, BOL, POD | "request POD/carrier evidence" message | M |
| Buyer portal | none | dispute submission | M |
| Insurer portal | policy doc | overdue notice; claim package submission (mock, only when ready) | M |
| Document storage | bundle docs | case file export (A) | M / A |

### D. Service capabilities (Sonny's 15)
| # | Capability | Handling | Tier |
|---|---|---|---|
| 1 | Monitor receivables | Queue plus scheduler tick on the sim clock surfaces overdue, short-paid and deadline items | M |
| 2 | Reconcile payments | Single-invoice: M. Multi-invoice allocation: A (C5) | M / A |
| 3 | Identify deduction reasons | From remittance / debit memo / email; otherwise request info | M |
| 4 | Gather evidence | Model-chosen tools plus `fetch_from_system` mock | M |
| 5 | Validate claims | Rules (code) plus model synthesis, with citations | M |
| 6 | Calculate adjustments | Rules only, integer cents | M |
| 7 | Resolve valid deductions | Credit memo proposal → approve → mock post | M |
| 8 | Dispute invalid deductions | Dispute proposal → approve → mock portal | M |
| 9 | Collect overdue | Follow-up drafts on the schedule | M |
| 10 | Manage buyer responses | Reply events → reconsideration. Counteroffer within authority: A | M / A |
| 11 | Monitor insurance | Notice deadline from the policy doc | M |
| 12 | File insurance claims | Claim package + readiness checklist + mock submission when ready. Real filing and loss calculation: D | M / D |
| 13 | Track insurer resolutions | A "Simulated" insurer response control only, excluded from metrics | A |
| 14 | Escalate exceptions | NEEDS_HUMAN with reason: missing evidence, conflict, legal authority missing, anomaly | M |
| 15 | Track outcomes | Separated money table (§8) | M |

Deduction types (Sonny's 9): early-pay discount, pricing, late delivery, damage, shortage, returns, promo/rebate, unexplained short pay, nonpayment/insolvency. **All 9 get rule handlers (M).** The fixtures must collectively cover at least 7. The demo shows shortage, promo, damage, unexplained short pay and nonpayment (insurer track). No case-id hardcoding: rules key off the reason and the documents, never the case id.

### E. Outputs
| Output | Handling | Tier |
|---|---|---|
| Recovery case | Case record plus status | M |
| Validity decision | Per-line decision, versioned | M |
| Credit memo / adjustment | Proposal → mock posted entry | M |
| Formal dispute | Proposal → mock portal receipt | M |
| Collection communications | Follow-up / info-request drafts → mock outbox | M |
| Insurance notifications | Notice proposal → mock insurer receipt | M |
| Claim package | Package plus readiness checklist | M |
| Insurance outcome record | Simulated only, labeled | A |
| Updated accounting | Mock ledger balance after posted credits | M |
| Audit trail | Append-only timeline: tools, decisions, edits (diff), approvals, receipts, stale events | M |
| Performance metrics | Bench outputs; the demo money table never sums tracks | M |

## 6. Case lifecycle
**Case status:** `open → investigating → (needs_info | needs_human | proposed) → awaiting_reply → closed`.
- New evidence or a ledger change on **any** case, including a closed one, moves it to `investigating`. A closed case is reopened, and the reopening is logged on the timeline.

**Insurer track badge:** `none | watching | notice_due | notice_submitted(mock) | claim_waiting | claim_ready | claim_not_ready | claim_submitted(mock)`.

**Proposal statuses:** `proposed | approved | rejected | stale | cancelled | submitted_mock`.

## 7. Approval rules
- **The agent acts on its own** when it reads, searches, extracts, runs rules, plans and drafts. None of these steps needs approval.
- **Approval is required** at the boundary where something leaves the system or changes the books: dispute, credit memo, message, insurer notice, claim package, correction, counteroffer.
- **What an approval binds:** the proposal version, recipient, amount, draft hash, evidence-set hash and decision version.
  - No standing rules, no bulk approve, no auto-approve.
- **Editable fields:**
  - draft text;
  - recipient, chosen from the case's allowed list;
  - per-line amounts, which can only go **down**.
- **Edits** create a new version, which is revalidated. Approved versions are immutable.
- **Reject** requires a reason.
- **Notice approval** shows the deadline and this caveat: *"Notice due by <date> under the policy terms in this file. Sending a notice does not establish coverage or claim eligibility."*
- **Submit** rechecks everything: the approval match, a current decision and evidence, readiness, and the ledger limits.
- **After a mock submit**, the card reads **"MOCK ACKNOWLEDGMENT — not sent to any real system"** plus the `MOCK-…` reference.

## 8. Money display (never summed)
| Column | Meaning | Demo value |
|---|---|---|
| Disputed (proposed / submitted mock) | Agent proposal; human-approved mock | real cents |
| Conceded (credit memo) | Proposed vs **posted** (mock) | real cents |
| Open ledger balance | Invoice − payments − **posted** credits | real cents |
| Balance subject to insurer notice | Same dollars as the dispute. Exposure, not "protected" | real cents |
| Accepted by buyer | Simulated only | "Simulated" or $0 |
| Cash collected | | **$0 always** |

The header never shows a combined total. Generated drafts must not **affirmatively assert** coverage, eligibility, payout, claim approval, recovery or a guarantee. A semantic check enforces this. Honest negated caveats, quoted policy wording (e.g. "not covered") and factual statements such as "cash collected: $0" are allowed.

Every screen labels its provenance:
- data is SYNTHETIC;
- actions are MOCK;
- the LLM runs in fake, replay or live mode.

## 9. Changing evidence and corrections
When a document arrives with a new version or changed content:
1. Decisions, readiness and live proposals computed on the old evidence go **stale**, and their approvals are voided.
2. Unsent work tied to them is cancelled.
3. Receipts and ledger entries are **never changed**.
4. The agent re-investigates automatically.
5. For each line, code compares the new decision with what has already been **posted or submitted**:
   - **More credit is owed:** an **incremental** credit memo for the difference only. The original concession is never reposted.
   - **Less should be disputed:** a **correction** that withdraws the difference from the earlier dispute receipt, linked to that receipt.
   - **More should be disputed:** a supplemental dispute.
   - **Over-credited:** escalate to a human. Reversals are out of scope.
6. Ledger changes (a posted credit) make any notice or claim draft stale if it was built on the old balance.

An identical redelivery of a document changes nothing. A conflicting redelivery of the same version escalates to a human.

## 10. Demo script (≈5 min; all data SYNTHETIC; offline FakeLLM path plus a live/replay segment)
**Fixture timeline for H** (computed from the fixtures, not hand-picked):
- Invoice INV-1042 dated 2026-08-03, due 2026-09-02.
- Sim day 0 = 2026-10-20.
- Policy P-A (synthetic): MEP 60 days after due → 2026-11-01. Notice within 30 days of that → **deadline 2026-12-01 (day 42)**. Claim window opens 60 days after the notice receipt.
- Follow-up 14 days after each outbound buyer action (company policy).
- `recoup advance --to-next-due` jumps to each boundary.

1. **Day 0, case H** (Acme Foods Co. → Northwind Grocers):
   - Invoice: SKU-1 400 cs × $78.00 + SKU-2 200 cs × $84.00 = **$48,000.00**. Paid $41,760.00.
   - **D1 shortage**, SKU-1, 40 cs, $3,120.00. POD v1 is signed and shows 400 received → **invalid** (proven). Dispute $3,120.00.
   - **D2 promo FALL26**, $3,120.00. Contract: earned = true, cap $1,800.00 → **partial**. Credit $1,800.00; dispute $1,320.00.
   - The trace shows the model choosing the POD, the contract and the emails.
   - The user approves the credit memo: MOCK-CM, balance $6,240.00 → **$4,440.00**.
   - The user edits the dispute text, then approves and submits it: **$4,440.00**, MOCK-DISP-0001.
   - Insurer badge: notice due 2026-12-01.
2. **Day 3, reconsideration** (automatic on advance):
   - **POD v2** supersedes v1: received SKU-1 360, refused 40, exception "40 cs crushed, refused at dock".
   - An inspection report arrives the same day, dated within the claim window.
   - D1 is recomputed: (400 − 360) × $78.00 = **$3,120.00 valid**.
   - New proposals: a **correction** withdrawing $3,120.00 from MOCK-DISP-0001, and an **incremental credit** of $3,120.00 for D1. The D2 credit is **not** reposted.
   - After posting, the balance is **$1,320.00**, the remaining dispute is D2 at $1,320.00, and the notice basis updates.
   - **Variant:** if the dispute was approved but not yet sent at day 3, it goes stale and is cancelled, and a fresh dispute for D2 ($1,320.00) replaces it. No correction is needed.
3. **Day 17:** buyer silence 14 days after the correction receipt → follow-up draft → approve → MOCK-MSG.
4. **Day 35** (deadline − 7): notice due → the notice draft cites P-A clauses, with balance basis $1,320.00 → approve with the caveat → MOCK-INS.
5. **Day 95:** the claim window opens → claim package checklist:
   - ✓ invoice, ✓ POD v2, ✓ contract
   - ✓ collection history (follow-up receipt)
   - ✗ **statement of account missing**
   - ⚠ the disputed $1,320.00 is restricted under P-A's "excluded until resolved" clause

   Status: **not ready**. Submit is blocked, and the info request lists the statement.
6. **Case C (concede):** pricing deduction of $500.00 on SKU-7 (1,000 × $0.50). An authorized amendment email (VP Sales, effective before the invoice date) sets the price to $10.00 vs the invoiced $10.50 → **valid** → credit memo only.
7. **Case N (needs info):** $20,000.00 invoice, $17,850.00 paid, no remittance or memo → line U1 **unexplained short pay** $2,150.00 → info request. No dispute.
8. **Live proof** (needs a key and approved spend, or a labeled recording of a live session): the model investigates an **unseen** case, then a renamed variant and a hidden-POD variant. The trace differs each time, and the result stays correct or honestly says needs_info. If neither a key nor a recording exists, the demo says so.
9. **Bench panel:** §11, with denominators and losses shown.

**Policy P-B** (used in a regression case) contrasts with P-A:
- MEP 90 days; notice within 15 days;
- `notice_still_required` while disputed;
- a credit limit below the balance, which marks the claim item restricted.

## 11. Benchmark (functional view)
- **Offline gates:** fixture replay, a deterministic scorer, simulator self-tests (scripted REF and BAD controllers), and a leakage test.
- **Track S (static):** the same model with a plain prompt vs the harness, on identical inputs and output schema.
- **Track T (episodes C1–C4):** a minimal tool loop vs the harness on the same model. Both get the same tools, world, events, clock, approver and one outer budget. A chat with no tools is never scored on Track T.
  - C1 multi-tool investigation;
  - C2 changing evidence and correction;
  - C3 deadline and follow-up;
  - C4 claim readiness.
- **Metrics:**
  - strict success over N_planned;
  - false disputes, counted as heavily as misses;
  - unsafe or unapproved writes, duplicate sends, missed deadlines, eligibility assertions;
  - cost = returned tokens × a dated, sourced price.
- **No-key handling:** without a key or approved spend, live rows read NOT EVALUATED. Scripted REF results are never presented as product capability.
- **Holdout:** authored by the Recoup Bench bot (not a tuner) and committed before any tuning. Planning target: Sun Nov 8, 1:00 PM PT or later (unconfirmed).

## 12. Out of scope (said plainly in the demo)
- Real sends or connectors.
- Real insurer filing.
- Legal advice.
- Multi-currency: USD only. Any non-USD or mixed-currency case goes to NEEDS_HUMAN.
- Auth or multi-user.
- Production robustness.
- OCR accuracy claims.
- Any pricing or free-tier claims.

## 13. Unknowns (marked honestly, not blocking)
- Judging rubric: unknown.
- Demo day: TBD.
- Model key: unverified. The offline path is required regardless.
- "jev": unidentified. It is not a dependency.
- Teammate invite acceptance: unverified.

