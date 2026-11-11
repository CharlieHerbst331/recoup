# ALDER-2718 — actual live evaluation, November 10, 2026 PT

SYNTHETIC data. MOCK actions. LLM live: `claude-haiku-5-5`.
One new case, two separately preserved loads; no renamed or hidden-document
variant and no general capability/benchmark acceptance claim.

The browser is left on Alder Market Cooperative, invoice JP-INV-2718, with
Haiku's saved dispute draft expanded. The selected saved database is now
`/data/recoup.db`, opened with the existing **Open saved run** control. No action
was approved or submitted. Open ledger balance remains 107200 cents.

## Evidence and custody

- Source-only input: `cases/unseen/alder-2718/bundle.json` (SHA-256 in manifests).
  New buyer, invoice, transaction dates, amounts, identifiers and three deductions.
  Only supported document kinds/fields; no oracle, decisions, proposals, rationale,
  tool traces or action sequence in input. USD integer cents throughout.
- `EVALUATOR-CHECKLIST.md` was written before either live load, held locally and
  never uploaded as evidence. Assessment below occurred after the first run ended.
- The required shared World epoch is 2026-10-20; transaction dates are new.
  Both POD versions are present at load. The higher version is authoritative
  under design/02 §3.6; supersession is not an event we injected mid-investigation.
- `live/history.json`, `live/chronology.jsonl`, `live/view.json`, and
  `live/recordings/*.json` preserve actual saved activity, full harness requests,
  normalized provider responses, tool arguments/results, decisions and proposals.
  Trace ordinals in `ACTIVITY.md` refer to stored order, not simulated-time sorting.
  `live/drafts.md` renders the actual saved wording. No artifact was edited.
- All 18 successful live response recordings match their model trace results.
  All saved draft texts match actual model `draft_proposal` arguments. Decision
  and proposal citation evidence is active. See `artifact-verification.json`.
- The deployed harness/adapter differ from this checkout. Source snapshots and
  deployed hashes are preserved. Local rules and app-loader hashes match the
  deployment. Offline tests verify this checkout; live observations describe
  the deployed code. No runtime code was changed for this task.

## What happened in the first, unseen live load

The capture runner reused the existing server environment in memory (no secret
values exported), confirmed live mode/model and new case ID, then invoked
`app.build(...).load([new source bundle directory])`. It did not call model tools,
seed a decision, tell the model expected steps, approve, or submit. The first
load used the database documented in the older shared-backend handoff,
`/data/recoup.db`. It was initially not the browser's selected database.

Actual chronological highlights:

| Trace ordinals | Recorded behavior |
|---|---|
| 10–27 | Haiku listed/read evidence, ledger and corrected POD; ran rules; proposed all three cited decisions; looked for damage evidence in the mock shipping system (not found) and planned missing evidence. |
| 28–35 | Haiku incorrectly treated dispute readiness as a prerequisite for a shortage credit. It repeated the same AM-SHORT readiness call/result, triggering the loop guard before any proposal existed. |
| 37–63 | The unchanged scheduler investigated again for pending load events. Haiku re-read evidence, searched for damage/inspection evidence, found no email attachment, and wrote the credit and dispute drafts. Its first information request incorrectly targeted the buyer portal; the recipient gate rejected it. Haiku corrected it to the allowlisted dock email and saved it. |
| 64–71 | Haiku requested approval of all three exact proposal versions, scheduled a 12-day recheck, and called `end`. The gate accepted with `unmet=[]`. Approval requests did not create human approvals. |
| 72–79 | Scheduler event acknowledgments reused accepted investigation work. |
| 80–105 | Another automatic investigation re-read sources and rules. Haiku again confused dispute readiness with credit readiness, claimed it was withholding the shortage credit, queued the other two proposals and ended. The gate again accepted `unmet=[]`. The earlier shortage approval request remained in history. |
| 106–108 | Remaining events were acknowledged. No pending events remained. |

Totals: **18 model responses, 68 tool calls, 1 saved decision, 3 saved proposals,
18 new immutable response recordings, 2 accepted ends, 0 human approvals,
0 receipts, 0 action attempts**. Recorded usage: 786959 input tokens and 24366
output tokens across the automatic investigations; no price/cost claim is made.

## Checklist comparison: Haiku versus deterministic code

| Deduction | Haiku's actual investigation/wording | Deterministic result and saved artifact |
|---|---|---|
| AM-SHORT | Used corrected signed POD v2 (112 accepted oat cases), distinguished it from the superseded entry, and proposed a valid deduction. Saved rationale describes the eight-case shortage. | Rules determined valid 52000 cents, disputed 0. Saved MOCK credit proposal `67bb9da1-1eeb-4ce6-a13a-407f2dab230f`, v1, recipient `juniper-erp.invalid`. |
| AM-DISC | Read the ten-day discount term and invoice/payment dates, proposed invalid, and wrote a buyer dispute requesting any signed amended terms. | Rules determined valid 0, disputed 25200 cents. Saved dispute `9ae84b08-a086-4beb-a2c2-0200044c0b93`, v1, recipient `alder-portal.invalid`. |
| AM-DAMAGE | Recognized that the debit is only a buyer claim and that the inspection/refused quantity is missing. Searched/fetched without finding it and wrote a targeted dock request. Did not invent a damaged quantity. | Rules returned needs_info / missing_evidence, missing `refused.BROTH-CASE`, with no valid/disputed Money. Saved information request `9b5929e1-1914-4edc-a859-93865d3ab6eb`, v1, recipient `dock@alder.example.invalid`, no monetary amount. |

Haiku's raw requested verdicts matched the rule findings. The harness still
normalizes proven verdicts, and tools populate rule-based amounts/citations;
these are not model calculations. The ledger did not change after loading the
source invoice/payment. Recipient checks rejected the wrong target. Superseded
POD v1 does not appear in saved decision/proposal citations. There was no insurance
policy, insurance proposal, coverage promise, approval or external submission.

Representative saved model wording (full drafts in `live/drafts.md`):

> The broth damage claim AM-DAMAGE (ref QA-2718-BROTH, reported September 24)
> cannot be evaluated yet.

> Please send the dock inspection record and any refused-quantity record for
> BROTH-CASE on this delivery.

The deployed harness supplies code-derived candidate kinds, line selections,
recipients, citations **and templated draft suggestions** after a decision.
Haiku explicitly observed those suggestions (trace 28). This is assisted
investigation, not independent discovery of every proposal. The final saved
wording differs from those suggestions and matches the model's actual tool
arguments; canned UI briefs and the H/C/N journey are not evaluation evidence.

## Defects and limits

1. Haiku misapplied **dispute** readiness to a supported **credit**, and initially
   objected to the correct ERP recipient because it was not the buyer. This
   caused the recorded loop escalation. Those are model workflow errors, not
   missing financial evidence.
2. Haiku selected an invalid information-request recipient once. The deterministic
   gate blocked it, and Haiku repaired it without intervention.
3. Its last `end` narrative says the credit was NOT queued, but earlier trace 65
   actually queued that proposal. It also used the phrase “no policy applies”
   after finding no policy document; absence of supplied policy is all the
   evidence establishes. These are narrative defects, not new rule conclusions.
4. Haiku restated amounts/dates and arithmetic despite the system's instruction
   against doing so. The recorded numbers agree with the sources/rule outputs;
   saved financial amounts remain code-owned. This run does not prove prompt
   compliance on that instruction.
5. The final persisted status remains `needs_human`, with the **earlier** exact
   reason: `loop; unmet: ALDER-2718:credit_memo:AM-SHORT, ALDER-2718:dispute:AM-DISC,
   ALDER-2718:info_request:AM-DAMAGE`. Later accepted ends did not clear that old
   status/reason. Consequently the stored status and latest completion gate
   disagree. We preserved both, without declaring a clean harness run.
6. The material damage evidence is genuinely absent. Human review must approve
   each proposal and obtain the dock inspection/quantity before any damage
   conclusion. The shortage credit does not require dispute readiness.

Completion assessment: **the first run eventually met design/02 §5.6 (two
accepted ends with no unmet criteria), and proposals are ready for human review;
it did not produce a clean single investigation or a consistent final status.**
Nothing has been posted, sent, collected or approved.

## Separately preserved app-default database attempt

Inspecting the live browser revealed a newer React host with a hardcoded default
`/data/react-recoup.db`; its current browser selection was actually a third saved
simulation, `/data/react-runs/simulation-f37f2ea546704c2da82289f3e90e52e5.db`.
That explains why reloading the browser initially showed only its H/C/N cases.

The same source bundle was loaded separately through the same normal service
path into the React default database before discovering the browser selection.
This is a **repeat-case attempt**, not additional unseen-case proof. The adapter
stopped with the exact preserved error **`ValueError: Conflicting replay recording`**.
No retry/fallback or recording replacement was performed. See
`live-app/exception.json`, `live-app/outcome.json`, and the separate capture archive.

That attempt has 0 committed model/tool traces, decisions or proposals; 12 load
events remain pending, and the case remains `investigating / evidence changed`.
The existing adapter records before returning a response, and the event
transaction rolls back on this exception, so a failing provider response/request
is not available in the saved trace. Do not interpret zero committed model calls
as evidence that no provider request occurred. Its exact returned content is
unavailable; it has not been reconstructed or invented.

Both databases' pre-existing case-history hashes and all pre-existing recording
hashes remained unchanged. The failed database was not used to fabricate the
browser result. The existing **Open saved run** control opened the original,
actually evaluated `/data/recoup.db`, and the UI visibly displayed ALDER-2718 and
its stored live dispute draft. The prior saved simulation remains intact.

## Verification and changed files

`make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint/format PASS,
**1156 passed, 2 skipped** in 162.12 seconds. Automated tests stayed offline,
used app.build and in-memory SQLite; the separate two fixture tests also passed.
The skips are existing optional OCR tests. See `make-check.txt`.

`CHANGED-FILES.md` lists every file created/changed by this task, including the
18 original response copies and both captures. Existing unrelated dirty source
and deployment files were preserved. Required done/next/question entries were
appended to Sonny's existing progress log. Stop after this one case step.
