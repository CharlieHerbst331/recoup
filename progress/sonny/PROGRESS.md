# Sonny progress

## 007-0 — 2026-11-07 (America/Los_Angeles)

### Session template

You are working in the Recoup repo (https://github.com/CharlieHerbst331/recoup) on branch 007-0-rule-test-vectors. You are the only agent in this session. Do the work yourself.
Read AGENTS.md and docs/INDEX.md first (before F0, read the bundle file named in your handoff instead). Design: docs/design/01-functional-design.md and 02-technical-design.md. Read only the sections this step names.
OWNERSHIP: you may create or edit only: recoup/engine/**, tests/engine/**, progress/sonny/**. Do not edit anything else. If you need a contract change, write it in progress/sonny/CONTRACT_REQUEST.md and continue against the current contract.
STEP: Implement PR 007-0 exactly as written in docs/specs/007-sonny-engine.md (step 007-0), including every listed test. Normative definitions: docs/design/02-technical-design.md §3.7, §5.3. Those sections are the only source; do not restate or reinterpret them in code comments. If the spec and design/02 seem to disagree, design/02 wins. Stop and write progress/sonny/CONTRACT_REQUEST.md instead of guessing. Stay inside your owned paths. Finish with make check green and a PR titled "007-0: rule test vectors".
SELF-CHECK BEFORE DONE: 1) run make check and paste the tail; 2) for each acceptance item, name the test that proves it; 3) for a bug fix, show the test failing before and passing after; 4) list changed files and revert any outside OWNERSHIP; 5) append done/next/question to progress/sonny/PROGRESS.md. Then stop. Do not start the next step.

### Inputs and scope

Read the supplied bundle's spec 007, handoff 007, session template, harness instructions, design/02 §3.7 and §5.3, and referenced hero numbers in design/01 §10. No root AGENTS.md or docs/INDEX.md exists in this checkout. Bundle status is pre-F0, design review pending. The repository has no commits and no configured remote; the branch is an unborn branch based on the existing unborn main. Saved an identical bundle copy at ~/recoup-007-sonny-bundle.md as instructed. The original untracked input bundle remains untouched.

Created only data and Markdown; no recoup imports, copied contract types, dependencies, product code, or executable test modules. Did not begin 007-1.

### Verification and acceptance evidence

The following named checks were run with a transient Python standard-library validation command. They validate fixture data only, not rule implementation. Future engine tests must execute every vector after F0; no engine test is claimed to pass today.

| 007-0 acceptance | Evidence/check | Result |
| --- | --- | --- |
| JSON vectors in §3.7 vocabulary | data-json: 14 parsed JSON files, 74 unique IDs; money/rate fields checked as integers | Pass |
| Every reason and missing evidence | all-reasons-and-missing: all nine reasons and missing-evidence expectations for each | Pass |
| Contradiction and unauthorized cases | authority: amendment_same_date_conflict, amendment_unauthorized_role, amendment_missing_author; late_pod_tracking_conflict | Pass for data presence/expectations; runtime pending |
| Gross basis with prior credit | hero-and-credit: gross_basis_prior_credit expected 6000/4000; downstream new credit reference 4000 | Pass for expected data; runtime pending |
| U1 versus NP | intake-isolation: 10 intake vectors, including zero payment with deduction lines | Pass for expected data; runtime pending |
| Hero D1 before/after and D2 | hero-and-credit: four hero snapshots with expected 0/312000, 312000/0, and 180000/132000 for D2 twice | Pass for expected data; runtime pending |
| Tolerance and money consistency | boundaries and money-invariants: seven tolerance vectors, negative deduction, 64 rule expectations | Pass |
| Engine instructions | recoup/engine/AGENTS.md copied verbatim from harness/AGENTS-engine.md | Pass |
| Progress note | This file | Present |
| make check green, offline | Attempted; required Makefile absent | Blocked |
| PR titled 007-0: rule test vectors | No source commit or remote configured in this checkout | Not created |

The spec-wide acceptance items for model authority, FakeLLM trace labels, and later-step tests are not applicable to data-only 007-0. They remain pending their named implementation steps. This is not a bug fix, so before/after failing-test evidence is not applicable.

`make check` tail (exit 2):

```text
make: *** No rule to make target `check'.  Stop.
```

Validation output:

```text
PASS data-json: 14 files, 74 unique vectors
PASS all-reasons-and-missing: 9 reasons, each with missing evidence
PASS money-invariants: 64 rule expectations; integer cents and verdict consistency
PASS boundaries: 7 tolerance cases and negative claimed
PASS authority: unauthorized/missing signer and same-date conflict
PASS hero-and-credit: 4 hero snapshots and gross prior-credit example
PASS intake-isolation: 10 intake vectors, mutually exclusive U1/NP expectations
NOTE these checks validate fixture data; no engine exists here to execute it
```

### Changed files

- recoup/engine/AGENTS.md
- tests/engine/vectors/README.md
- tests/engine/vectors/amendments.json
- tests/engine/vectors/boundaries.json
- tests/engine/vectors/damage.json
- tests/engine/vectors/early_pay_discount.json
- tests/engine/vectors/hero.json
- tests/engine/vectors/intake.json
- tests/engine/vectors/late_delivery.json
- tests/engine/vectors/nonpayment.json
- tests/engine/vectors/pricing.json
- tests/engine/vectors/promo_rebate.json
- tests/engine/vectors/returns.json
- tests/engine/vectors/shortage.json
- tests/engine/vectors/trust.json
- tests/engine/vectors/unexplained_short_pay.json
- progress/sonny/PROGRESS.md

Ownership audit: all 17 created repository files are within the three allowed paths. No existing file was modified; no out-of-ownership change required reverting. External bundle copy was explicitly requested by the handoff.

DONE: 007-0 data and required notes prepared; 74 vectors pass data-integrity checks. Full verification and PR creation remain blocked by the empty checkout.
NEXT: Put these owned files on the actual main-based repository branch, run make check using Charles's harness, and open "007-0: rule test vectors"; 007-1 waits for F0.
QUESTION: The checkout has no upstream history or remote. The initialized Recoup checkout is needed to complete make check and create the PR.

## 007-0 follow-through — 2026-11-08 (America/Los_Angeles)

This entry supersedes the earlier checkout, check-target and PR blockers.

### Session template

You are working in the Recoup repo (https://github.com/CharlieHerbst331/recoup) on branch 007-0-rule-test-vectors. You are the only agent in this session. Do the work yourself.
Read AGENTS.md and docs/INDEX.md first (before F0, read the bundle file named in your handoff instead). Design: docs/design/01-functional-design.md and 02-technical-design.md. Read only the sections this step names.
OWNERSHIP: you may create or edit only: recoup/engine/**, tests/engine/**, progress/sonny/**. Do not edit anything else. If you need a contract change, write it in progress/sonny/CONTRACT_REQUEST.md and continue against the current contract.
STEP: Implement PR 007-0 exactly as written in docs/specs/007-sonny-engine.md (step 007-0), including every listed test. Normative definitions: docs/design/02-technical-design.md §3.7, §5.3. Those sections are the only source; do not restate or reinterpret them in code comments. If the spec and design/02 seem to disagree, design/02 wins. Stop and write progress/sonny/CONTRACT_REQUEST.md instead of guessing. Stay inside your owned paths. Finish with make check green and a PR titled "007-0: rule test vectors".
SELF-CHECK BEFORE DONE: 1) run make check and paste the tail; 2) for each acceptance item, name the test that proves it; 3) for a bug fix, show the test failing before and passing after; 4) list changed files and revert any outside OWNERSHIP; 5) append done/next/question to progress/sonny/PROGRESS.md. Then stop. Do not start the next step.

### Repository and validation

Fetched upstream main at 89675c0b6ac676fa28c3475f58134689b74c274c and based the previously unborn branch on it, preserving the owned files. Read upstream AGENTS.md, docs/INDEX.md, spec 007 step 0, and design/02 §3.7 and §5.3. They agree with the supplied bundle. Upstream describes F0/design review as pending, so the work remains data only.

Installed Python 3.11.18 and the unchanged project's pinned dependencies in /tmp/recoup-007-check. Used the Makefile's existing PYTHON variable; changed no dependency or build files. The setup downloads completed before the offline test run.

Command: `make check PYTHON=/tmp/recoup-007-check/bin/python` (exit 0).

```text
/tmp/recoup-007-check/bin/python -m ruff check recoup tests
All checks passed!
/tmp/recoup-007-check/bin/python -m ruff format --check recoup tests
21 files already formatted
RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest
...
tests/contracts/test_stubs.py ........                                   [ 98%]
tests/contracts/test_tools.py ....                                       [100%]

============================= 201 passed in 0.83s ==============================
```

### Final acceptance mapping

The named `check_*` checks below are transient standard-library assertions run against the JSON; they are not persisted executable test modules. This preserves the pre-F0 data-only restriction. The 201 repository tests validate the existing contracts; they do not execute the future rules engine.

| Acceptance for step 007-0 | Named evidence | Result |
| --- | --- | --- |
| §3.7 facts and expected findings in JSON | check_json: 14 files, 74 unique synthetic vectors; vocabulary audit of every document field and integer cents/basis points | PASS |
| Every reason, including missing evidence | check_reason_coverage: exact nine-reason set, each with a missing-evidence vector | PASS |
| Contradictions and unauthorized amendments | check_conflict_and_authority: amendment_same_date_conflict, late_pod_tracking_conflict, amendment_unauthorized_role, amendment_missing_author | PASS |
| Gross prior-credit example | check_gross_credit_and_hero: gross_basis_prior_credit expected 6000/4000 and downstream reference 4000 | PASS |
| U1 versus NP | check_boundaries_and_intake: ten intake scenarios, including zero-paid deductions and tolerance boundary | PASS |
| Hero D1 before/after POD v2 and D2 | check_gross_credit_and_hero: four hero snapshots | PASS |
| Tolerance and consistent expected money | check_money_invariants: 64 findings; check_boundaries_and_intake: seven tolerance cases plus negative claimed | PASS |
| Engine AGENTS.md from harness | check_instruction_copy: byte equality with docs/harness/AGENTS-engine.md | PASS |
| Progress and ownership | This entry and staged-path audit against upstream main; 17 owned files, listed above | PASS |
| Offline make check green | Existing Makefile: Ruff lint, Ruff format and 201 pytest tests | PASS |
| All listed 007-0 tests | All data checks above; 007-0 specifies vectors, not a pre-F0 rules implementation | PASS for step 007-0; runtime execution deferred to 007-1 |

The spec-wide model-authority and FakeLLM trace acceptance belongs to later implementation steps and is not asserted by this PR.

One instruction-copy formatting mismatch was found and fixed. Before: `check_instruction_copy` failed because the source's trailing blank line was missing. After copying the source bytes: `check_instruction_copy` passed. No product bug fix or rules implementation was made.

The changed-file list is the same 17 files listed in the prior entry. Upstream files outside ownership are unchanged. The original bundle remains an untouched, unstaged input; its external copy is preserved. No out-of-ownership source changes required reverting.

DONE: 007-0 data, exact engine instructions and acceptance evidence are ready; make check passed, 201 tests.
NEXT: Publish PR "007-0: rule test vectors", then Reviewer → Verifier. Do not begin 007-1 before F0.
QUESTION: None; no contract change was needed.

### Publication

PR: https://github.com/CharlieHerbst331/recoup/pull/1 — **007-0: rule test vectors**, targeting main.

Final whitespace audit preserved the harness AGENTS.md's existing trailing blank line intentionally; `git -c core.whitespace=-blank-at-eof diff --check` passed. The exact instruction-copy assertion also passed. All 17 PR files are inside ownership; the original input bundle is untracked and excluded.

DONE: Published PR #1 for 007-0; make check green (201 tests), data acceptance checks passed, and ownership audited.
NEXT: Reviewer → Verifier; await F0 before starting 007-1. No next-step work started.
QUESTION: None.

## 007-0 r10 — 2026-11-08 (America/Los_Angeles)

### Repository and retained implementation

Read `~/recoup-007-sonny-bundle-r10.md`, prompt 007-0, external design/04 §1–5,
spec 007 step 0, design/02 §2, §3.2–3.7, §5.3, and actual candidate interfaces,
testing stubs, models, money, oracle, dependency configuration and AST DAG test.
The external r10 test-lane exception authorizes the owner-local unit support here.

Verified origin is `https://github.com/CharlieHerbst331/recoup.git`. Initial branch
was clean `main`, tip `fc425ce` (owner acceptance documentation), preceded by
`89675c0` (candidate contracts), then `a60dc8d` (initial commit). `git fetch origin`
succeeded. Candidate `89675c0b6ac676fa28c3475f58134689b74c274c` exists as a commit.
No required owned predecessor for 007-0. Discovered and retained prior owned 007-0
implementation on `origin/007-0-rule-test-vectors`, actual tip
`54076cb7160274db64f598698b359193bba41e40` (includes `d360422` vectors).
Created `007-0-vectors-and-owned-test-support` from that tip, without merging,
resetting or discarding work. Main's later documentation commit is not merged.

Before implementation, both candidate ancestry and retained owned-tip ancestry
passed `git merge-base --is-ancestor <sha> HEAD` (exit 0). The command
`git diff --exit-code 89675c0b6ac676fa28c3475f58134689b74c274c HEAD -- recoup/contracts`
also passed (exit 0). Candidate contracts remain unchanged.

### Scope and acceptance evidence

Preserved all 74 existing JSON vectors across 14 files (64 rule, 10 intake).
Added contract-model factories and narrow clock/fact-set scripts in owned tests;
reused shared ScriptedLLM. No production rules, policy, readiness, World, app or
other later-step implementation was introduced. Engine instructions now match the
external r10 harness/AGENTS-engine.md exactly (transient byte-equality check PASS).

| 007-0 acceptance | Persistent evidence | Result |
| --- | --- | --- |
| JSON envelope, scalar/key shape and integer cents/rates | test_vector_envelope_and_scalar_vocabulary | PASS |
| All reasons, each with missing facts; unique IDs | test_unique_ids_and_reason_coverage | PASS |
| Typed DeductionLine/FactSet/LedgerEntry inputs, expected money invariants | test_rule_vector_contract_inputs_and_expected_money | PASS |
| Every source/revision citation resolves using actual shared resolver | test_every_effective_fact_citation_resolves | PASS |
| Contradictions, unauthorized amendments, gross prior credit, seven tolerance boundaries and hero D1/D2 snapshots | test_critical_expectations_are_present | PASS |
| Typed, mutually exclusive U1/NP expectations and collection-only NP route | test_intake_expectations_are_typed_and_mutually_exclusive | PASS |
| Confirmed OCR/vision facts use human-confirmed revisions and fact locators | test_confirmed_money_is_revision_with_fact_locator | PASS |
| Independent fixture values and unreadable document without facts | test_factory_results_do_not_share_mutable_fields | PASS |
| Script argument/order/consumption checks; unexpected methods raise | test_world_script_checks_arguments_order_and_consumption, test_wrong_arguments_and_unconsumed_script_fail | PASS |
| Offline shared LLM script and exhaustion | test_shared_scripted_llm_stays_offline_and_exhausts | PASS |

The inherited `negative_claimed` expectation is a case escalation, not an instance
of RuleFinding: actual Verdict has no needs_human member (design/02 §3.2, §5.3).
The data check preserves it separately without inventing an enum/model. Resolving
its eventual engine/controller representation belongs to the later consumer step;
no shared symbol/signature blocks the 007-0 factories.

### Commands and results

Used existing `/tmp/recoup-007-check` Python 3.11.18; installed no dependencies.
No provider/network calls occur in tests. No paid APIs or external actions used.

- Initial authored-check run: Ruff E731 on a lambda assignment; pytest 1 failed,
  161 passed, with KeyError: 'expected_route' in the U1 data check. Corrected the
  checks to use a def and the existing missing-reason expectation. No unrelated
  baseline error occurred; this was test-support authoring, not a product bug fix.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0, Ruff lint PASS,
  Ruff format PASS (26 files), pytest **362 passed in 0.45s**.
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine -q`:
  exit 0, **161 passed in 0.17s**.

Final make check tail:

```text
tests/engine/test_vectors.py ........................................... [ 68%]
........................................................................ [ 88%]
...........................................                              [100%]
============================= 362 passed in 0.45s ==============================
```

### Real integration acceptance (external design/04 §2–5)

| Required eventual real check | Status | Missing provider |
| --- | --- | --- |
| Replay U1/NP and fixture fact/history/hash/versioning cases through real loader/app | BLOCKED | Charles SqliteWorld and recoup.app.build at G1 |
| Replay prior-credit and hero evidence replacement through real persistence/cascade | BLOCKED | Charles real World transaction/cascade implementation at G2; actual engine derivation |
| Execute the rule vectors through real composed engine | BLOCKED | Sonny rules/engine/factory and Charles composition at G3 |

These are deferred integration requirements, not skipped tests or unit passes.
No integration test is claimed PASS. Reviewer/Verifier acceptance of actual
integration remains outstanding. The owner acceptance commit on main is distinct
from the external bundle's baseline review/verification status.

### Changed paths in this r10 session

- recoup/engine/AGENTS.md
- tests/engine/__init__.py
- tests/engine/doubles.py
- tests/engine/fixtures.py
- tests/engine/test_doubles.py
- tests/engine/test_vectors.py
- tests/engine/vectors/README.md
- progress/sonny/PROGRESS.md

All changes are owned. Shared contracts, root documentation, build/dependency files
and original JSON vectors are untouched. No push, merge or PR publication performed.

DONE: 007-0 r10 unit-lane support and persistent data acceptance pass; existing vectors/commits retained; implementation tip recorded below.
NEXT: Reviewer/Verifier review; real integration remains BLOCKED as enumerated. Stop this session; no 007-1 or 007-2 work.
QUESTION: None for 007-0; missing integration providers remain explicit.

### Actual retained 007-0 implementation tip

Branch: `007-0-vectors-and-owned-test-support`.
Implementation tip: `5be383e8a6dedb36d3dd6f79854685202ab50af5`.
This actual commit contains the complete r10 implementation and check evidence;
the following bookkeeping commit only records its SHA. Dependent sessions must
retain this tip (and its owned ancestors), per external design/04 §5.

DONE: Recorded actual 007-0 implementation tip 5be383e8a6dedb36d3dd6f79854685202ab50af5.
NEXT: Stop; real integration and independent review/verification remain outstanding.
QUESTION: None for the authorized 007-0 unit-lane scope.

## 007-1 r10 — 2026-11-08 (America/Los_Angeles)

Read the external r10 handoff prompt 007-1, design/04 §1–5, spec 007 step 1,
design/02 §2, §3.7, §5.3, repo root/engine instructions, docs index, actual
candidate models/money/resolver and retained 007-0 support. Applied the explicit
external r10 unit-lane exception without modifying root/docs instructions.

### Predecessor preservation

Initial clean branch: `007-0-vectors-and-owned-test-support`, HEAD
`e9fa60b` (007-0 tip-record bookkeeping), following implementation
`5be383e8a6dedb36d3dd6f79854685202ab50af5`, bookkeeping `54076cb`, vectors
`d360422`, candidate `89675c0b6ac676fa28c3475f58134689b74c274c`.
Resolved the required 007-0 implementation SHA from this progress file, not from
an assumed main tip. Before implementation these commands all exited 0:

- `git merge-base --is-ancestor 89675c0b6ac676fa28c3475f58134689b74c274c HEAD`
- `git merge-base --is-ancestor 5be383e8a6dedb36d3dd6f79854685202ab50af5 HEAD`
- `git merge-base --is-ancestor 54076cb7160274db64f598698b359193bba41e40 HEAD`
- `git diff --exit-code 5be383e HEAD -- tests/engine`
- `git diff --exit-code 89675c0 HEAD -- recoup/contracts`

Created `007-1-rules` from that intact descendant (`git switch -c`), then normal
`git fetch origin` succeeded. No reset, rebase, merge, push or work loss. All
14 original JSON files, 74 vectors (64 rules / 10 intake), and 007-0 support
remain unchanged. Intake execution belongs to Charles's loader, not this step.

### Implementation and acceptance

Added pure `run_rules` for all nine reasons, using shared types and Money helpers.
No World/app dependency, network, paid API, new dependencies or external action.
References for business semantics remain design/02 §3.7 and §5.3.

| Acceptance | Persistent test | Result |
| --- | --- | --- |
| Every 007-0 rule vector, boundaries, amendments, damage windows, returns inventory, hero snapshots, flags, money/verdict invariants | test_every_rule_vector (64 vectors) | PASS |
| Confirmed origin=fact money, exact supplied citation, shared resolver | test_confirmed_fact_only_money_and_citation (OCR/vision) | PASS |
| Legal readable vs absent/unreadable inventory | test_legal_authority_inventory | PASS for explicit pure guard; automatic consumer routing unresolved |
| Gross valid/disputed independent of prior credit | test_prior_credits_never_reduce_gross_rule_amounts | PASS |
| Duplicate ref, remittance mismatch, claimed exceeds total flags | test_duplicate_and_math_flags, test_claim_exceeds_line_total_flag | PASS |
| No case-ID branching | test_case_identity_does_not_affect_rules | PASS |
| Zero without facts, U1 missing reason without invoice | test_zero_claim_needs_no_facts, test_u1_sku_does_not_require_invoice_to_request_reason | PASS |
| Authorized email override, order-independent result | test_authorized_email_amendment_and_order_independence | PASS |
| NP invalid and collection-only action family | test_every_rule_vector[np_balance_owed] | PASS for pure rule/action selector; actual proposal later |
| NP with classified buyer dispute | test_nonpayment_with_classified_buyer_dispute_requires_info | PASS for supplied classification; consumer encoding unresolved |

`NeedsHumanError` is a local exception, not a copied/new contract model. Negative
claims abort evaluation before any findings are returned. Legal guard is explicit;
no undocumented legal trigger is guessed. See CONTRACT_REQUEST.md for exact
consumer seams requiring Charles's decision. No 007-2 implementation was started.

### Commands/results and failures resolved

- First rule-test run: 70 passed / 2 failed, both test-authoring errors calling
  the shared resolver with wrong argument order and expecting a nonexistent
  `.valid` result. Read actual resolver; corrected to its scalar-returning API.
- Added edge regression tests: 74 passed / 3 failed (zero claim with no facts,
  U1 SKU without invoice, input-order-dependent citations). Fixed rule evaluation
  ordering and deterministic fact ordering; repeated run: **77 passed**.
- Initial Ruff authoring errors were line length/import formatting; corrected
  using existing Ruff. No baseline failures or hidden skips.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0; Ruff lint PASS,
  Ruff format PASS (28 files), pytest **439 passed in 0.46s**.
- Final owned tests/checks are recorded with the implementation-tip entry below.

### Real integration acceptance

| Required actual integration | Status | Missing provider |
| --- | --- | --- |
| Replay rule vectors/returns document status/confirmed revisions against actual loaded FactSets | BLOCKED | Charles real SqliteWorld and recoup.app.build at G1 |
| Gross prior-credit basis and hero evidence replacement preserve receipts and ledger | BLOCKED | Charles transaction/cascade World at G2, later actual derivation |
| NP produces approved collection-only proposal and escalations become actual case status | BLOCKED | Actual engine/derivation/factory at G3 plus Charles composition; candidate questions above |

No unit double is integration proof. Reviewer/Verifier real integration acceptance
remains outstanding. The actual World/app files are absent in this checkout.

### Changed files (007-1 only)

- recoup/engine/rules.py
- tests/engine/test_rules.py
- progress/sonny/CONTRACT_REQUEST.md
- progress/sonny/PROGRESS.md

DONE: 007-1 independent rules and tests implemented; make check green; 007-0 preserved.
NEXT: Resolve documented consumer seams and run real G1/G2/G3 integration when providers exist; stop this session, no 007-2.
QUESTION: Charles to resolve the escalation/legal/email-classification consumer seams in CONTRACT_REQUEST.md; no shared changes made.

### Actual 007-1 implementation tip and final verification

Branch: `007-1-rules`.
Implementation tip: `d8d9e83b7c00433209574094af7317916c5b6904`.
The next bookkeeping commit records this actual SHA without changing implementation.

Final `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0, Ruff lint and
format PASS, **439 passed in 0.51s**. Final owned command
`RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine -q`:
exit 0, **238 passed in 0.17s** (77 rule tests, 161 retained 007-0 tests).
`git diff --check`: PASS. Final byte-preservation diffs for all 007-0 fixtures,
test support and tests, and candidate shared contracts: exit 0. Changed paths are
exactly the four listed above. No failing tests remain; integration is BLOCKED,
not passed or silently skipped.

DONE: Committed 007-1 implementation d8d9e83b7c00433209574094af7317916c5b6904; checks pass and all required predecessor commits remain ancestors.
NEXT: Stop; no 007-2, push, merge, PR publication or external action performed.
QUESTION: Remaining real providers and candidate consumer seams are documented above and in CONTRACT_REQUEST.md.

## 007-2 r10 — 2026-11-08 (America/Los_Angeles)

Read only prompt 007-2 in `~/recoup-007-sonny-bundle-r10.md`, its spec step,
external design/04 §1–5, design/02 §2, §3.7, §3.8, §5.6, root/engine instructions,
docs index and actual candidate models/interfaces/money/resolver/tools. The
explicit external r10 unit-lane exception applies. Reviewed all existing
CONTRACT_REQUEST.md entries; the three earlier consumer questions remain open
but do not prevent this step's independent policy/readiness implementation.

### Repository and predecessor checks

Initial branch `007-1-rules`, clean working tree, HEAD
`762c8213a876052b8a019efc0855be50cf7fe37d` (user's latest 007-1 commit).
History retained 007-1 implementation `d8d9e83b7c00433209574094af7317916c5b6904`,
007-0 bookkeeping `e9fa60b`, implementation
`5be383e8a6dedb36d3dd6f79854685202ab50af5`, earlier 007-0 commits, and candidate
`89675c0b6ac676fa28c3475f58134689b74c274c`. Required 007-0 tip and preserved
007-1 implementation tip were resolved from the preceding progress entries.

Before implementation, all four `git merge-base --is-ancestor <SHA> HEAD` checks
for candidate, 5be383e, d8d9e83 and 762c821 exited 0. Full `git diff --exit-code
762c8213a876052b8a019efc0855be50cf7fe37d HEAD` and candidate contract diff both
exited 0. Created `007-2-policy-and-readiness` from that exact HEAD using
`git switch -c`; normal `git fetch origin` succeeded. No main merge, reset,
rebase, push or loss of earlier work.

### Independent implementation and acceptance evidence

Added pure `policy.answer` and `readiness.dispute/notice/claim` against the
existing shared models/signatures. Business definitions remain design/02 §3.7,
§5.6; receipt identification uses §3.8. No World double was necessary for these
pure functions. Used hand-built actual contract inputs, no other owner fixtures.
No model/API/network calls, external actions, dependencies or shared changes.

| 007-2 acceptance | Test evidence | Result |
| --- | --- | --- |
| Separate lines on one FactSet, confirmed vs unconfirmed facts/conflict, mismatched line | test_two_lines_isolated_confirmed_and_unconfirmed | PASS |
| Current citation membership and actual shared resolver on supplied raw fixture | test_dispute_citations_current_membership_and_resolver | PASS for each separately; integrated raw resolution BLOCKED below |
| Receipt-sensitive claim date, no receipt, latest notice and waiting boundary | test_claim_window_uses_receipt_date_and_latest_receipt | PASS |
| Text-only exclusion absent until extracted effective fact; distinct source/fact citations round-trip | test_exclusions_extracted_fact_citations_survive_json | PASS |
| One missing exclusion clause does not hide another answer | test_exclusion_failure_does_not_hide_other_exclusions | PASS |
| Notice a/b/c, missing POD independence, uncertain findings annotation | test_notice_independence (5 cases) | PASS |
| Unknown applicability/deadline, missing clause, submitted dispute annotation | test_notice_submitted_unknown_clause_and_applicability | PASS |
| POD absent/unreadable/unsigned/signed, fixed claim item ids, no eligibility field | test_claim_pod_inventory (4 cases) | PASS |
| Two contrasting synthetic policies | test_contrasting_policies (2 cases) | PASS |
| Claim checklist, history/receipt alternatives, restrictions | test_claim_checklist_restrictions_missing_and_history | PASS |
| POD completeness scoped to inventoried evidence, multiple candidates | test_claim_documents_multiple_candidates_and_same_evidence_signature | PASS |
| Unconfirmed vision POD and unknown policy requirements | test_claim_unconfirmed_pod_and_missing_policy_terms | PASS |
| Applicability and date boundaries | test_applicability (4 cases) | PASS |
| Textual answer provenance and missing clause | test_textual_answers_require_effective_clause_facts | PASS |
| Unsupported/untrusted/conflicting terms; pure inputs | test_invalid_policy_terms (3 cases), test_policy_untrusted_conflict_and_purity | PASS |
| Net ledger balance and due boundary | test_notice_due_boundary_and_net_ledger_balance | PASS |
| No case-id selection of policy behavior | test_case_identity_does_not_select_policy_behavior | PASS |

### Commands/results

Used existing `/tmp/recoup-007-check` Python 3.11.18, without dependency changes.
Initial authoring lint found line lengths/import formatting; existing Ruff fixed
formatting. Initial tests: 25 passed / 1 failed because the test omitted required
`DeductionLine.reason`; corrected the typed fixture. Expanded edge tests pass.
No unrelated baseline failures occurred. No product bug fix was claimed.

- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine/test_policy_readiness.py -q`:
  **31 passed**, exit 0.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0, Ruff lint PASS,
  Ruff format PASS (31 files), **470 passed in 0.65s**.
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine -q`:
  **269 passed in 0.22s**, exit 0; includes every retained 007-0/007-1 test.
- `git diff --exit-code 762c8213a876052b8a019efc0855be50cf7fe37d -- recoup/engine/AGENTS.md recoup/engine/rules.py tests/engine/fixtures.py tests/engine/doubles.py tests/engine/test_doubles.py tests/engine/test_vectors.py tests/engine/test_rules.py tests/engine/vectors recoup/contracts`:
  exit 0; all predecessor implementation/tests/vectors and contracts preserved byte-for-byte.
- `git diff --check`: PASS.

Final make check tail:

```text
tests/engine/test_vectors.py ........................................... [ 75%]
........................................................................ [ 90%]
...........................................                              [100%]
============================= 470 passed in 0.65s ==============================
```

### Genuine integration blockers and remaining independent work

| Required real acceptance | Status | Missing provider/resolution |
| --- | --- | --- |
| Same policy/readiness cases using actual loaded FactSet/DocStatus/extracted revisions | BLOCKED | Charles SqliteWorld + recoup.app.build at G1 (absent in checkout) |
| Pure dispute citation predicate plus raw backing-quote/revision resolution | BLOCKED | Charles clarification of FactSet validation boundary; request #4 in CONTRACT_REQUEST.md; actual World.resolve_citation in consumer |
| Notice/claim behavior after actual receipt/ledger changes and staleness | BLOCKED | Charles actual persistence/transactions/cascade at G2 |
| Tool adapters preserve answers and composed engine uses the three readiness functions | BLOCKED | Subsequent owned tools/engine/factory, Charles composition at G3 |

Unit passes do not constitute real integration PASS. Reviewer/Verifier must pass
actual integration before integrated completion. Raw citation membership is
implemented; independent full raw-text/revision resolution is not possible with
the pure signature as currently supplied. This is disclosed rather than hidden
behind a fake resolver or copied evidence model. Everything else in 007-2's
independent unit lane is implemented. The earlier 007-1 questions remain open.

Future independent work is available in 007-3 (tools/gates/derivation with owned
scripted ports), followed by injection-based 007-4/5, plus independent 007-6 SDK
stub adapter work after its documentation prerequisite. None was started here.
Real integration still requires real providers; no paid/live proof is authorized.

### Changed paths (007-2 only)

- recoup/engine/policy.py
- recoup/engine/readiness.py
- tests/engine/test_policy_readiness.py
- progress/sonny/CONTRACT_REQUEST.md
- progress/sonny/PROGRESS.md

Only assigned owned paths changed. Root/docs, shared contracts, dependencies,
build files and every 007-0/007-1 implementation/test file remain unchanged.

DONE: 007-2 independent policy/readiness implemented and tested (470 full / 269 engine / 31 new tests); predecessors preserved; integration and raw-resolution boundary explicitly outstanding.
NEXT: Commit this step, record actual implementation tip, then stop; future 007-3 work remains a separate session.
QUESTION: Charles to resolve request #4's raw citation-validation boundary and the unchanged 007-1 consumer questions; real providers required for integration acceptance.

### Actual 007-2 implementation tip

Branch: `007-2-policy-and-readiness`.
Implementation tip: `b47813d6e4370abe0c907fd2606471ba85e5afee`.
This commit contains the complete independently implemented scope, acceptance
evidence and request #4. A following bookkeeping commit records this actual SHA.
The working tree was clean after the implementation commit. Required candidate,
007-0 and retained 007-1 tips remain ancestors. No next-step work, push or merge.

DONE: Committed 007-2 implementation b47813d6e4370abe0c907fd2606471ba85e5afee; make check and all engine tests pass.
NEXT: Stop this session; real integration and raw-citation boundary acceptance remain BLOCKED as recorded above.
QUESTION: Request #4 and prior consumer questions await Charles; no further independent 007-2 work identified without that resolution.

## 007-3 r10 — 2026-11-08 (America/Los_Angeles)

Read root/engine instructions, docs index, spec 007 step 3, design/02 §3.4–3.8,
§5.4–5.6 and §8.1, the referenced design/01 §10 hero example, and the downloaded
r10 handoff/design/04 §1–5. Applied its explicit owned unit-lane exception.
No other owner paths, dependencies, shared models or prior implementations changed.

Started from clean `007-2-policy-and-readiness`, HEAD `36b9d74`.
The candidate `89675c0b6ac676fa28c3475f58134689b74c274c`, actual 007-1 tip
`d8d9e83b7c00433209574094af7317916c5b6904`, and actual 007-2 tip
`b47813d6e4370abe0c907fd2606471ba85e5afee` all passed
`git merge-base --is-ancestor <SHA> HEAD` (exit 0). Created
`007-3-tools-gates-derivation` on that intact descendant. No reset, rebase,
merge, push, PR publication, network/model call or external action occurred.

### Independent implementation and acceptance

Added `tools.py` with the case-bound ToolSessionFactory/ToolSession over the
actual shared registry, validated quoted fact extraction, code-owned decisions,
policy/readiness adapters, drafting, scheduling, approval requests, completion
checks and full tool-envelope traces. Product schemas exclude bench tools.
Added `derive.py` and `gates.py`; their semantics refer to design/02 §3.8,
§5.4–5.6. Static export uses §8.1 and current-clock claim readiness.

| 007-3 acceptance | Independent test evidence | Result |
| --- | --- | --- |
| Quoted fact accepted; fabrication, wrong key/evidence and empty/invalid quote rejected | test_propose_fact_quote_validation_and_schema, test_fact_rejects_invalid_key_or_quote | PASS |
| Dollar/cents extraction and OCR/vision trust | test_money_fact_dollars_or_cents, test_fact_preserves_extraction_trust, test_quote_sign_does_not_fabricate_positive_money | PASS |
| Superseded citation rejected and case scoping | test_superseded_fact_and_cross_case_citations_rejected | PASS |
| Excessive edited credit and unsupported edited dispute at save/approve/submit; lower edit permitted | test_edited_credit_and_dispute_rechecked_at_all_stages | PASS |
| Assertion fail / caveat / cited quote / factual cash statement | test_assertion_check_rejects_affirmative_outcomes, test_assertion_check_passes_caveats_cited_quotes_and_ledger | PASS |
| Assertion scope and neutral review requests | test_assertion_negation_scope_regressions, test_assertion_neutral_requests_and_post_target_negation, test_uncited_policy_quote_does_not_bypass_assertions | PASS |
| Hero correction + incremental credit; no repost; approved-unsent variant | test_hero_correction_incremental_credit_and_no_repost, test_hero_approved_unsent_needs_no_correction | PASS |
| Receipt allocation and correction/supplement sequence keys | test_receipt_level_corrections_newest_first_and_sequences | PASS |
| Per-line readiness isolation | test_per_line_readiness_does_not_block_other_line | PASS |
| Exact readiness tool errors | test_readiness_argument_errors (4 cases) | PASS |
| Static claim checklist export, no policy → empty | test_static_output_claim_items_at_evaluation_clock | PASS |
| Proven verdict/money cannot be supplied by model | test_tool_decision_never_accepts_model_verdict_or_money, test_gate_independently_rejects_forged_decision_money | PASS |
| Gate raw-resolution and trust boundary | test_gate_resolves_rule_citations_even_when_draft_omits_them, test_unconfirmed_money_cannot_enter_credit_gate | PASS with actual shared resolver and owned raw fixtures |
| Notice balance and claim save/approve vs submit gates | test_notice_and_claim_gate_lifecycle_and_no_loss_amount | PASS |
| Other tool routing, policy answers, no automatic approval, scope/limits, schedule/end gates | test_unknown_and_bench_tools_rejected_and_no_automatic_approval, test_read_search_list_scope_and_limits, test_exclusion_tool_preserves_distinct_answers, test_schedule_and_end_gate, test_missing_plan_and_product_end_after_proposals, test_followup_completion_is_bound_to_latest_outbound_receipt | PASS |
| Target/recipient/hash/duplicate/amount and stale/overcredit checks | test_gate_target_recipient_hash_duplicates_and_amounts, test_derivation_overcredit_and_stale_decision_fail_closed | PASS |

`ToolWorld` is narrow owned unit support using actual contract records and the
shared resolver. Its `record` installs explicit receipt fixtures; it is not a
submit implementation, transaction system, or persistence proof. No tests claim
otherwise. The validator re-resolves backing citations through the World port;
request #4's real FactSet producer/pure-function boundary remains awaiting Charles
and real-provider verification. Earlier legal/email consumer questions remain
unchanged. The assertion check is deterministic and phrase-based; the listed
language cases are verified, not arbitrary natural-language classification.

### Commands, failures and regressions

Used existing `/tmp/recoup-007-check` Python 3.11.18; installed nothing.
Initial authoring run: 33 passed / 10 failed. Nine failures came from test
fixtures bypassing enum validation and incorrect expected receipt ordering or
waiting-period status; corrected typed inputs/expectations. A real assertion-scope
failure allowed unrelated negation to mask an affirmative outcome; fixed it.
The signed-price regression initially accepted positive cents from `-$78.00`;
fixed value matching. Follow-on assertion regressions had 5 failures / 50 passes:
`not only`, unrelated `no delay`, `claim is approved`, and neutral review wording.
All now pass after scoping negation and neutral requests. No baseline failure
was hidden. Existing Ruff fixed authored formatting/import issues.

Final commands (all exit 0):

- `make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint PASS;
  Ruff format PASS (37 files); **527 passed, 12 skipped in 1.05s**.
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine -q -rs`:
  **326 passed, 12 skipped in 0.66s** (57 new unit checks; 269 predecessors).
- New unit module separately: **57 passed in 0.23s**.
- `git diff --check`: PASS.
- `git diff --exit-code 36b9d74 --` all contracts, prior engine files, previous
  fixtures/doubles/tests/vectors: PASS; predecessors preserved byte-for-byte.

Final make check tail:

```text
tests/engine/test_vectors.py ........................................... [ 78%]
........................................................................ [ 92%]
...........................................                              [100%]
======================= 527 passed, 12 skipped in 1.05s ========================
```

### Real integration acceptance — all BLOCKED, none PASS

Separate `test_007_3_integration.py` defers the allowed `recoup.app` import to its
fixture, obtains `build(RecoupConfig(db=":memory:"), controller=NullController()).world`,
and uses actual World reads/writes/approvals/receipts when available. Only absence
of `recoup.app` causes explicit per-case skips; installed-provider errors will fail.
Each skipped case states `BLOCKED G1/G2: recoup.app.build and real SqliteWorld are absent`.

| Real integration test | Cases | Status / missing provider |
| --- | --- | --- |
| test_real_propose_fact_and_fabrication | 1 | BLOCKED G1 app-built SqliteWorld/loader/facts |
| test_real_superseded_citation | 1 | BLOCKED G1/G2 actual evidence supersession |
| test_real_edited_allocations_rejected | 2 | BLOCKED G1/G2 real reads and engine validator port |
| test_real_assertion_gate | 4 | BLOCKED G1 real World inputs |
| test_real_hero_credit_correction_no_repost | 1 | BLOCKED G2 actual approval/submit/ledger/cascade |
| test_real_receipt_correction_allocation | 1 | BLOCKED G2 actual receipt accounting and versions |
| test_real_readiness_errors_and_isolation | 1 | BLOCKED G1/G2 loaded facts and supersession |
| test_real_static_claim_items | 1 | BLOCKED G1 actual loader and current-clock FactSet |

The integration module calls the engine validator explicitly against the real
World at each stage. Automatic World invocation of the actual Sonny validator
also requires Charles's composition with EngineParts at G3 (007-4 factory is the
next owned step); stub PassValidator is not finance-safety proof. Real transaction,
restart, concurrent-submit, and staleness enforcement cannot be certified here.
Reviewer/Verifier real integration acceptance remains outstanding. Green with
these twelve skips is independent completion only, not integrated acceptance.

### Changed files (007-3 only)

- recoup/engine/derive.py
- recoup/engine/gates.py
- recoup/engine/tools.py
- tests/engine/tool_support.py
- tests/engine/test_tools_gates_derive.py
- tests/engine/test_007_3_integration.py
- progress/sonny/PROGRESS.md

DONE: Implemented independent 007-3 tools/gates/derivation; 57 new checks pass and make check is green with twelve explicitly BLOCKED integration cases.
NEXT: Run real integration when G1/G2 providers exist, then actual validator composition at G3; stop this session without starting 007-4.
QUESTION: No new contract request; prior consumer questions and real-provider acceptance remain outstanding.

### Actual 007-3 implementation tip

Branch: `007-3-tools-gates-derivation`.
Implementation tip: `5c2223d42ffa066ce9ec8b6d219d013b02fef0b1`.
The following bookkeeping commit records this actual SHA and corrects the initial
fixture-failure count. No implementation changes followed the final checks.

DONE: Committed independent 007-3 implementation 5c2223d42ffa066ce9ec8b6d219d013b02fef0b1; all required predecessors remain ancestors.
NEXT: Stop; twelve real integration cases and automatic validator composition remain BLOCKED pending providers; no 007-4 work or external publication.
QUESTION: Charles's real providers and the existing consumer requests remain outstanding; no new shared-interface mismatch identified.

## 007-4 — 2026-11-08 (America/Los_Angeles)

Implemented the independent unit lane from the downloaded r10 handoff, applying
its explicit test-double exception. Read design/04 §1–5, design/02 §4.5,
§5.1–5.2, §5.8–5.10, the actual shared ports and prior tools/gates/derivation.
The initial tree was clean on `007-3-tools-gates-derivation`. Candidate
`89675c0b6ac676fa28c3475f58134689b74c274c` and required 007-3 implementation
`5c2223d42ffa066ce9ec8b6d219d013b02fef0b1` both passed ancestor checks.
Created `codex/007-4-harness-factory-ingestion` on the existing descendant.
No prior implementation, shared contract, dependencies or other owner path changed.

Added bounded HarnessEngine investigation, prompt/config, FakeLLM, exact-request
ReplayLLM recording/replay, factory/controller exports, and structured/text/text-PDF
ingestion with explicit failures. Definitions remain in design/02 §4.5,
§5.1–5.2, §5.6 and §5.8–5.10. Model responses and original wrong verdicts are
traced; tool execution uses the code-owned proven verdict. Tools retain authority
over amounts, citations, approvals and completion. The harness offers no send or
bench tools. Replay misses never fall back to a live call. OCR/vision are not
implemented or claimed in this step. Wall limits are checked at call boundaries;
a synchronous in-flight client must enforce its own transport timeout.

Acceptance evidence (all independent unit PASS):
- Hero day 0: `test_hero_day_zero_and_fake_trace` (444000 dispute, 180000 credit;
  per-line findings and fake provenance, no receipt or automatic approval).
- Mixed insured/missing POD isolation:
  `test_missing_pod_does_not_block_pricing_or_notice` and
  `test_no_insurer_recipient_still_computes_notice_readiness`.
- Completion: `test_end_refused_until_completion`.
- Loop/budgets: `test_loop_guard_and_keeps_prior_work`,
  `test_tool_error_budget`, `test_step_wall_and_empty_response_limits`,
  `test_budget_config_cannot_exceed_treatment`.
- Wrong proven verdict: `test_wrong_proven_verdict_is_overridden_and_original_traced`.
- Generated PDF usable through the actual fact tool and shared citation resolver:
  `test_generated_text_pdf_is_usable_by_fact_tool`.
- Extraction failures/structured/text/eml: `test_ingest_failure_statuses`,
  `test_encrypted_and_scanned_pdf`, `test_structured_text_eml_and_missing_file`.
- Factory/controller, protocol-only injected session, rules-only and replay:
  `test_factory_selection_and_controller_delegation`,
  `test_tool_session_injection_uses_only_protocol_methods`,
  `test_rules_only_has_no_model_calls`, `test_replay_exact_key_and_no_fallback`.
- Derivation safety escalation: `test_overcredit_is_escalated_without_discarding_state`.

Initial new suite: 20 passed / 3 failed. Two fixture errors were missing buyer
facts and a missing case_id argument. One implementation regression was an empty
LLM response not immediately exhausting a one-error budget. Corrected fixtures
and the error accounting; the same test now passes. Additional edge tests added
for overcredit escalation, missing insurer recipients and protocol-only sessions.

Commands (existing Python 3.11 environment; no installs or network):
- `/tmp/recoup-007-check/bin/python -m pytest tests/engine/test_harness_factory_ingest.py -q`:
  **26 passed**.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint/format PASS;
  **553 passed, 18 skipped in 1.10s** (exit 0).
- `git diff --check`: PASS.

Real integration in `test_007_4_integration.py`: six explicit BLOCKED cases,
none PASS. Missing providers: app.build/SqliteWorld at G1/G2, actual ingestor and
factory wiring at G3. Cases: `test_real_hero_harness`,
`test_real_mixed_insurance_isolation`, `test_real_completion_and_loop` (2),
`test_real_model_verdict_override`, `test_real_pdf_loader_factory_ingestor`.
The twelve existing 007-3 integration skips remain BLOCKED. No unit-double pass
is claimed as real loader, persistence, restart or automatic validator proof.

`HarnessEngine.handle` deliberately raises with the missing 007-5 prerequisite;
the exported controller delegates to it. Event/due-work behavior and automatic
app orchestration therefore remain unavailable until that separate step. Live
adapter selection explicitly reports the 007-6 prerequisite. Neither later step
was started. Reviewer/Verifier real integration acceptance remains outstanding.

Changed files (007-4 only):
- recoup/engine/config.py
- recoup/engine/factory.py
- recoup/engine/harness.py
- recoup/engine/ingest.py
- recoup/engine/llm/__init__.py
- recoup/engine/llm/fake.py
- recoup/engine/llm/replay.py
- recoup/engine/prompts/system_v1.md
- tests/engine/test_harness_factory_ingest.py
- tests/engine/test_007_4_integration.py
- progress/sonny/PROGRESS.md

DONE: 007-4 independent implementation and 26 new unit checks pass; make check is green with 18 explicitly blocked integration cases. Changes remain uncommitted.
NEXT: Stop this session; real 007-4 integration needs G1/G2/G3 providers, and controller event handling remains the separate 007-5 step.
QUESTION: No new contract mismatch; prior consumer requests and real-provider review/verification remain outstanding.

## 007-5 — 2026-11-08 (America/Los_Angeles)

Implemented the owned independent handler lane against design/02 §5.7 and the
existing shared ports, using the explicit r10 unit-double exception in the engine
instructions. Preserved the pre-existing, uncommitted 007-4 implementation and
progress entry. No shared contract, dependencies, root/docs, or other owner files
changed. Did not start 007-6, commit, publish, or perform an external action.

Added scheduler event/due processing and HarnessEngine delegation, notice
scheduling at the readiness tool boundary, claim-window rescheduling after policy
changes, and gate revalidation for case-wide scheduled follow-ups. Each item and
its acknowledgement share a World transaction. Generated follow-ups are proposals
only, labeled SYNTHETIC/MOCK/LLM mode; they never approve or submit themselves.
Normative behavior remains in design/02 §3.8, §5.5–5.7.

Acceptance evidence in tests/engine/test_scheduler.py (independent unit lane):
- Day 3 correction + incremental credit without repost:
  test_day_three_correction_incremental_credit_no_repost.
- Silence and repeat/reconstructed-engine no-op:
  test_silence_exactly_one_followup_and_restart_no_op.
- Buyer reply cancellation and late reply suppression:
  test_buyer_email_cancels_followup,
  test_reply_after_basis_suppresses_overdue_work_even_without_email_event;
  test_unrelated_email_does_not_cancel checks sender isolation.
- Notice deadline minus seven and claim package at claim window:
  test_notice_deadline_minus_seven_and_claim_window;
  test_direct_investigation_schedules_notice_once checks the tool boundary.
- Receipt replacement, company follow-up interval and sequence:
  test_new_receipt_replaces_followup_basis_and_uses_company_policy.
- Policy changes: test_policy_change_reschedules_claim_window.
- Exception rollback and retry:
  test_event_exception_rolls_back_then_retries_once,
  test_save_failure_rolls_back_event_before_ack,
  test_due_exception_rolls_back_proposal_and_ack.
- Gate revalidation: test_followup_revalidation_rejects_early_forged_and_replied.
- Event sequence and duplicate trace:
  test_duplicate_is_trace_only_and_events_sort_by_time_sequence.

The first unit run had five failures from writing a nonexistent ScriptedClock
attribute; fixed the new fixtures to use its actual start/current_day interface.
The same cases then passed. Updated the retained factory test to check an idle
handle instead of the removed 007-5 NotImplementedError. Added regressions for
policy-date changes and immediate post-save failures; these pass. Unit transaction
snapshots/reconstructed engines are deliberately owned test support and do not
prove actual SQLite durability or process restart. No copied contract models.

Real acceptance in tests/engine/test_007_5_integration.py: five explicitly BLOCKED
cases (all skipped because recoup.app is absent), covering day-3 release, silence,
buyer email, notice/claim dates and mid-event rollback using actual app-built
SqliteWorld when available. Real persisted restart acceptance also remains
BLOCKED pending the real provider; the current memory-only test port does not
expose a reopen operation. The prior eighteen integration skips remain unchanged.
Request #5 records the unavailable shared sequence for due-work ordering. The
implemented fallback is disclosed there; exact cross-kind sequence compliance
is not claimed. No real integration or durable-restart pass is claimed.

Changed files for this step only:
- recoup/engine/scheduler.py
- recoup/engine/harness.py (handle delegation in existing uncommitted 007-4 file)
- recoup/engine/tools.py
- recoup/engine/gates.py
- tests/engine/test_scheduler.py
- tests/engine/test_007_5_integration.py
- tests/engine/test_harness_factory_ingest.py (obsolete stub assertion only)
- progress/sonny/CONTRACT_REQUEST.md
- progress/sonny/PROGRESS.md

Verification: existing /tmp/recoup-007-check Python environment; no installations
or network. Focused scheduler suite: 14 passed. Final make check and diff audit
recorded below.

Final `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0; Ruff lint and
format PASS (50 files); **567 passed, 23 skipped in 1.97s**. `git diff --check`:
PASS. All nine step changes are within the assigned engine/tests/progress paths;
pre-existing uncommitted 007-4 files remain present. No outside-owner edits.

DONE: Implemented independent 007-5 handlers and fourteen unit checks; make check passes with twenty-three explicitly blocked integration cases overall.
NEXT: Stop this session; run real-provider integration and persisted-restart acceptance when G2/G3 are available.
QUESTION: Charles to resolve request #5 for cross-kind due sequence; real-provider acceptance and previous requests remain outstanding.

## 007-6 — 2026-11-08 (America/Los_Angeles)

Before writing the adapter, read the current official OpenAI Python tool-calling
examples and request/response reference on 2026-11-08:
- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/api/reference/python/resources/chat/subresources/completions/methods/create

Checked the installed, already pinned openai 3.46.0 constructor signature as well.
Implementation follows design/02 §4.5 and §5.9, using Chat Completions function
calling and the existing contract LLMResponse and ReplayLLM. Existing uncommitted
007-4/007-5 work is preserved. Tests use injected SDK-shaped clients under the
engine AGENTS.md explicit r10 unit-lane exception; no live request is authorized
or performed and no real model-investigation result is claimed.

Added OpenAICompatLLM with SDK Chat Completions translation for the shared tool
schemas and harness conversation, validated JSON-object tool arguments, explicit
live provenance, optional returned token counts, measured latency and transport
timeout with automatic retries disabled. Client failures, incomplete completions,
malformed call identities and invalid JSON fail without recording or fallback.
Successful responses are recorded through the existing ReplayLLM for exact replay.
The configured model identifier is retained for recording/replay, including when
the provider returns a resolved snapshot name. No amounts, verdicts, citations or
actions are computed or executed by this adapter.

Factory live selection now constructs the adapter; fake/replay paths are unchanged.
Model/base URL can come from the supplied config or RECOUP_MODEL/OPENAI_BASE_URL;
the official SDK reads OPENAI_API_KEY. Removed the predecessor's obsolete
NotImplementedError assertion; live selection is checked with a stub SDK factory.
No new dependencies, contract edits, network in tests, live spend, commit or
publication. Did not start 007-7.

Acceptance evidence: tests/engine/test_openai_compat.py has 19 passing cases:
- test_tool_round_trip_and_exact_replay checks actual contract schemas, two-turn
  conversation conversion, immutable inputs, live metadata and exact offline replay.
- test_text_without_usage_and_empty_tools and test_multiple_calls_preserved check
  optional usage/text and ordered parallel calls.
- test_bad_arguments_never_recorded (5), test_partial_responses_never_recorded (3),
  test_invalid_call_identity (3), test_empty_choices_fail_closed and
  test_client_error_propagates_without_record_or_fallback check failure boundaries.
- test_env_sdk_configuration_and_factory, test_required_model_and_timeout and
  test_real_sdk_reads_key_without_network check config, factory and installed SDK
  construction. Network connect operations are blocked throughout this test module.

Initial focused suite: 19 passed. Ruff reported one long authored test line;
formatting resolved it. Final make check (exit 0):

```text
make check PYTHON=/tmp/recoup-007-check/bin/python
All checks passed!
52 files already formatted
======================= 586 passed, 23 skipped in 2.28s ========================
```

The 23 pre-existing real-provider integration cases remain explicitly blocked;
this step claims offline adapter acceptance only. Real model investigation is
not verified. git diff --check passed. All changes for this session are owned:
- recoup/engine/llm/openai_compat.py (new)
- recoup/engine/factory.py (live selection only)
- tests/engine/test_openai_compat.py (new)
- tests/engine/test_harness_factory_ingest.py (removed obsolete assertion only)
- progress/sonny/PROGRESS.md (this entry and documentation URLs/date)

DONE: 007-6 live adapter, factory selection and ReplayLLM recording implemented; 19 new offline checks pass and make check is green (586 passed, 23 skipped).
NEXT: Stop after 007-6; real-provider integration and authorized live evaluation remain separate outstanding work.
QUESTION: No new contract or dependency request; existing provider blockers and prior requests remain outstanding.

## 007-7 — 2026-11-08 (America/Los_Angeles)

Implemented the independent engine scan lane against design/02 §5.8, preserving
all pre-existing uncommitted 007-4/5/6 work. Stayed inside engine/tests/progress;
no dependency installations, manifests, shared contracts, app/CLI or other owner
files changed. Stopped after this step; no 007-8 work, commit or publication.

Added capability reporting for the doctor owner, optional tesseract/pytesseract
image OCR, multi-frame input, scanned/mixed PDF page OCR, and explicit image
vision through the existing live adapter. PDF page rendering uses the existing
optional pdftoppm executable with a bounded subprocess; pytesseract also has a
30-second timeout. Native PDF text remains in page order alongside scan text.
OCR/vision fields carry their extraction trust, and the actual propose_fact tool
writes matching trust on cited facts. No model computes amounts. Unavailable,
empty and corrupt extraction paths return explicit contract statuses without
retaining supplied fields as a substitute for failed scan extraction.

The factory enables image vision only with config.vision, live mode, Pillow,
and a present API key. The config/environment mapping remains Charles's §4.5
composition responsibility. No vision request runs for the default fake path.
Vision requests transcribe images with no tools; successful SDK responses use
existing ReplayLLM recording. Tests cover exact image-request replay. Scanned
PDFs use OCR, not vision. This is an offline implementation, not evidence of
real transcription accuracy or model judgment.

Used the OpenAI Docs skill and read the official image-input guide on 2026-11-08
before implementing image requests:
https://developers.openai.com/api/docs/guides/images-vision?api-mode=chat

Acceptance evidence in tests/engine/test_scan_ingest.py (20 PASS, 2 SKIP):
- Always-run missing capability: test_ocr_unavailable (image and scanned PDF).
- Capability/key/mode gating: test_capability_probe_and_vision_gate and
  test_factory_vision_requires_flag_live_and_key.
- Actual propose_fact trust propagation: test_scan_trust_reaches_actual_fact_tool
  (ocr/vision), using the authorized owned unit-double lane.
- PDF page isolation/order: test_pdf_missing_pages_use_ocr_in_page_order.
- Actual installed PDF renderer, with stub OCR only:
  test_real_pdf_renderer_with_stub_ocr. This is not a real OCR pass.
- SDK-shaped multimodal request and exact recorded replay:
  test_vision_sdk_image_request_and_exact_replay; no network or live spend.
- Frame order/timeouts: test_ocr_backend_uses_timeout_and_preserves_frame_order.
- Failures: test_scan_backend_failures (3),
  test_empty_scan_cannot_use_supplied_fields,
  test_pdf_renderer_missing_is_unavailable, test_pdf_renderer_failure_is_unavailable,
  test_ocr_execution_failure_is_unavailable (2),
  test_invalid_image_is_corrupt_with_available_backend,
  test_vision_client_failure_is_unavailable, test_vision_tool_calls_are_rejected.
- Real optional OCR: test_real_tesseract_image and test_real_scanned_pdf explicitly
  SKIPPED because tesseract and pytesseract are absent. Pillow/pypdf and the PDF
  renderer are available. No real OCR or vision acceptance is claimed.

Updated the two predecessor failure-status tests to force unavailable OCR, so
expectations remain deterministic on machines with or without optional tools.
Initial focused runs exposed two fixture mistakes (missing case_id, then checking
EffectiveFacts instead of the test port's appended revisions); corrected both.
The first full check rejected a variable-name dynamic import in the capability
probe. Replaced it with literal module imports and reran make check successfully.
No shared guard was changed or bypassed.

Final verification (existing /tmp/recoup-007-check environment, no network):

```text
make check PYTHON=/tmp/recoup-007-check/bin/python
All checks passed!
54 files already formatted
======================= 606 passed, 25 skipped in 2.40s ========================
```

Focused scan suite: 20 passed, 2 skipped. git diff --check: PASS. The 23 existing
real-provider integration skips remain unchanged. Actual doctor wiring is
BLOCKED by the absent CLI/app providers. Request #6 records that seam and the
optional PDF renderer prerequisite for Charles. No integrated doctor, real OCR,
or live vision pass is claimed from green unit tests.

Changed files for 007-7 only (all within ownership):
- recoup/engine/scans.py (new)
- recoup/engine/ingest.py
- recoup/engine/factory.py
- tests/engine/test_scan_ingest.py (new)
- tests/engine/test_harness_factory_ingest.py (two deterministic failure fixtures)
- progress/sonny/CONTRACT_REQUEST.md (request #6)
- progress/sonny/PROGRESS.md (this entry)

DONE: Implemented the independent 007-7 OCR and optional image vision paths; make check passes with 606 passed and 25 skipped.
NEXT: Stop; Charles to wire doctor and resolve the PDF renderer prerequisite; execute real OCR/vision acceptance only when those paths are available.
QUESTION: Request #6 covers absent doctor/composition and the optional PDF renderer; existing real-provider blockers remain outstanding.

## 007-8 — 2026-11-08 (America/Los_Angeles)

Reviewed root/engine instructions, docs/INDEX, spec 007 step 007-8, design/01
§4–5, design/02 §3.2, §3.6–3.8, §5.4–5.5, and the actual shared bundle,
proposal/tool/ledger models and World ports. The handoff names counteroffers
and multi-invoice allocation but the normative financial behavior and shared
allocation seam are missing. Requests #7–8 in CONTRACT_REQUEST.md identify the
specific decisions and consumer acceptance needed from Charles. No code or
tests were added around invented financial definitions; existing counteroffer
rejection remains in force. Neither 007-8 feature is implemented or verified.

Preserved all pre-existing uncommitted engine/tests/progress work. This session
changed only progress/sonny/CONTRACT_REQUEST.md and progress/sonny/PROGRESS.md.
No shared contracts, dependencies, docs or other owner files changed; no commit,
publication or external action. Stopped after the 007-8 contract review.

Verification: `make check PYTHON=/tmp/recoup-007-check/bin/python` exited 0:

```text
All checks passed!
54 files already formatted
======================= 606 passed, 25 skipped in 2.87s ========================
```

The 25 existing skips remain; green checks verify the existing implementation,
not acceptance of either ambition feature. No bug fix or new acceptance pass
is claimed. `git diff --check` passed.

DONE: Reviewed 007-8 and recorded blocking definition/contract requests #7–8; existing make check passes (606 passed, 25 skipped).
NEXT: Implement only 007-8 once Charles supplies normative counteroffer and multi-invoice allocation definitions and confirms the shared seams.
QUESTION: Charles to resolve requests #7–8; no financial behavior was guessed and no contract was copied or changed.

DONE: Prepared all 21 pending files for commit and push; make check PYTHON=/tmp/recoup-007-check/bin/python passed (606 passed, 25 skipped); git diff --check passed. Files: progress/sonny/CONTRACT_REQUEST.md, progress/sonny/PROGRESS.md, recoup/engine/config.py, recoup/engine/factory.py, recoup/engine/gates.py, recoup/engine/harness.py, recoup/engine/ingest.py, recoup/engine/llm/__init__.py, recoup/engine/llm/fake.py, recoup/engine/llm/openai_compat.py, recoup/engine/llm/replay.py, recoup/engine/prompts/system_v1.md, recoup/engine/scans.py, recoup/engine/scheduler.py, recoup/engine/tools.py, tests/engine/test_007_4_integration.py, tests/engine/test_007_5_integration.py, tests/engine/test_harness_factory_ingest.py, tests/engine/test_openai_compat.py, tests/engine/test_scan_ingest.py, tests/engine/test_scheduler.py.
NEXT: Push this commit to origin/codex/007-4-harness-factory-ingestion and stop.
QUESTION: Existing contract requests and integration skips remain unresolved; no new question for this push.

## Integration follow-up after Charles merge — 2026-11-08 (America/Los_Angeles)

Starting tip: 45f99c8. Completed one integration repair step using the actual
app.build/SQLite providers now present. Baseline make check reproduced Charles's
audit: 874 passed, 7 failed, 2 skipped. All seven failures were stale decision
bindings; the existing regression report additionally identified claim item IDs.

The engine now retains an equivalent current decision after validating all
submitted lines and citations (design/02 §3.7, §3.8, §5.2 and §5.5). Changed
rationale, lines or evidence basis still creates a new decision. Approval and
submission checks remain active. Added real app-built tests for repeated
investigation with approval preservation and successful MOCK submission, line
order equivalence, rationale revision and evidence-basis changes. Existing
scheduler acceptance verifies day-3 correction/credit, silence/reply handling,
notice/claim scheduling and rollback with the actual providers.

Policy answers retain the claim_doc key so readiness exports the §5.6 item IDs,
including separate requirements of the same document kind and fact-locator
citations. Updated engine tests that expected document-kind IDs and added a
repeated-kind/key/citation regression. No shared contracts, fixtures, ownership
instructions, dependencies or other-owner implementation files changed.

Verification:
- make check PYTHON=/tmp/recoup-007-check/bin/python: ruff lint/format PASS;
  884 passed, 2 skipped. All 23 formerly provider-blocked engine integration
  tests now execute and pass, plus two new real-provider regression tests.
- RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m recoup.cli check-regression:
  r01–r08 all PASS (8/8), actual engine runtime, exit 0.
- Actual recoup.cli doctor: engine installed, text PDF available, OCR packages
  and tesseract unavailable, vision disabled/no configured key; no network check.
- git diff --check: PASS.

The two remaining skips are optional real image/scanned-PDF OCR tests. No live
vision or real OCR acceptance is claimed. Request #6's CLI absence is superseded
by the merge, but shared doctor capability reporting/PDF renderer confirmation
remain outstanding. Cross-kind due ordering and selected-case routing still
need the previously recorded owner/contract decisions. Requests #7–8 remain
blocked: the pulled design/contracts do not define counteroffer derivation or
multi-invoice allocation. These are not implemented by this integration repair.

Every changed file:
- recoup/engine/tools.py
- recoup/engine/policy.py
- recoup/engine/readiness.py
- tests/engine/test_007_3_integration.py
- tests/engine/test_007_4_integration.py
- tests/engine/test_policy_readiness.py
- tests/engine/test_tools_gates_derive.py
- progress/sonny/PROGRESS.md

DONE: Completed newly unblocked provider integration repairs; make check passes (884 passed, 2 OCR skips), actual regression 8/8 PASS.
NEXT: Stop after this integration step; changes remain uncommitted for review.
QUESTION: Charles's existing financial definitions, selected-case routing, ordering and scan-composition decisions remain outstanding; no new shared seam was invented.

DONE: User requested publication of the eight integration-repair files listed above; pre-commit make check passed again (884 passed, 2 OCR skips), and git diff --check passed.
NEXT: Commit and push the current branch, including the already merged Charles history, then stop.
QUESTION: No new question; existing shared-definition and optional capability blockers remain as recorded above.


## Charles prerequisites merge and handoff review — 2026-11-09 (America/Los_Angeles)

User requested both merging Charles's published branch and reviewing the handoff
for the next step. Clean starting branch: codex/007-4-harness-factory-ingestion,
tip 9c821adb23d645eea0173ad42900e23d8574ff4e. Fetched origin and fast-forwarded
origin/006-2b-sqlite-world-core-and-app-build to 933ab05. No conflicts or manual
changes to Charles-owned files. This session implements no subsequent engine step
and does not push the branch.

Read docs/INDEX.md, spec 007, and Charles's SONNY-UNBLOCK-ACCEPTANCE,
SONNY-FINANCIAL-HANDOFF and SONNY-WORLD-HANDOFF. Shared candidate pin:
75a58397bec3846847673ef8af4c7ae85d2a5264; contracts tree:
fb064458d4070d7290bd0f242a28d56f1c31aac7. These handoffs supersede the historical
shared-definition blockers; they do not establish remaining engine acceptance.

Next implementation step is 007-8 in owned engine/tests paths: counteroffer
derivation, semantic gates, offer_ref tool flow, completion/FakeLLM and handler
integration, with app-built in-memory approval/MOCK-submit acceptance. Normative
references: design/02 §3.7–3.8 and §5.4–5.5. Current derive.py has no counteroffer
branch; gates.py explicitly rejects counteroffers. Multi-invoice allocation is
already implemented by Charles under §3.9: verify ordinary invoice balances and
handler re-investigation, without a second allocation implementation.

Remaining consumer review should also cover legal and buyer classification
(§3.7, §5.3), citation rechecks (§3.7), selected-case routing (§3.5, §4.5),
event/due ordering (§5.7), and shared scan reporting (§5.8). Concrete observed
gaps: scheduler._buyer_email currently checks portal recipients only, and
engine.scans.scan_capabilities still duplicates the probe instead of delegating
to contracts.capabilities. These are follow-up findings, not changes in this step.
No Carter prerequisite remains in the handoff.

Verification (existing environment; no dependencies installed):
- make check PYTHON=/tmp/recoup-007-check/bin/python: exit 0; Ruff lint/format
  pass, 969 passed and 2 optional OCR skips in 17.83s. Includes H/C/N app engine
  acceptance and real engine scheduler/investigation integration tests.
- RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m recoup.cli --db :memory:
  check-regression: exit 0; r01–r08 all PASS, actual engine runtime.
- No live model calls or real external actions performed.

Every file imported by the fast-forward (existing Charles commits):
- cases/ambition/README.md
- cases/ambition/counteroffer/bundle.json
- cases/ambition/multi-invoice/remittance.json
- docs/design/02-technical-design.md
- docs/specs/007-sonny-engine.md
- progress/charles/CONTRACT_REQUEST.md
- progress/charles/PROGRESS.md
- progress/charles/SONNY-FINANCIAL-HANDOFF.md
- progress/charles/SONNY-UNBLOCK-ACCEPTANCE.md
- progress/charles/SONNY-WORLD-HANDOFF.md
- recoup/app.py
- recoup/cli.py
- recoup/contracts/capabilities.py
- recoup/contracts/interfaces.py
- recoup/contracts/models.py
- recoup/contracts/remittance.py
- recoup/contracts/testing.py
- recoup/contracts/tools.py
- recoup/world/remittance.py
- recoup/world/store.py
- tests/app/doubles.py
- tests/app/test_factory_unit.py
- tests/app/test_financial_intake.py
- tests/app/test_mutations_integration.py
- tests/app/test_scoped_controller.py
- tests/cli/test_financial_intake.py
- tests/cli/test_routing.py
- tests/contracts/test_capabilities.py
- tests/contracts/test_design_contract.py
- tests/contracts/test_financial_extensions.py
- tests/contracts/test_models.py
- tests/world/test_counteroffer_boundary.py
- tests/world/test_remittance.py

Only newly edited file in this session: progress/sonny/PROGRESS.md.

DONE: Fast-forwarded the current branch to Charles's 933ab05 and reviewed the handoffs; make check passes (969 passed, 2 OCR skips), regression 8/8 PASS.
NEXT: Implement 007-8 counteroffer consumers and app-built acceptance, then verify remittance and the remaining cited consumer seams; stop after this merge/review step.
QUESTION: None; the shared decisions are available, and no Carter dependency remains. Merge is local; the progress entry remains uncommitted.

## 007-8 implementation — 2026-11-09 (America/Los_Angeles)

Executed only 007-8 against Charles's final publication
933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f on
006-2b-sqlite-world-core-and-app-build (also the starting local HEAD). Shared
implementation candidate 75a58397bec3846847673ef8af4c7ae85d2a5264 and contracts
tree fb064458d4070d7290bd0f242a28d56f1c31aac7 remain the handoff pins.
Preserved the pre-existing uncommitted merge/review progress entry. No protected
files, dependencies or other owner's implementation changed; no commit or push.

Implemented engine counteroffer derivation, semantic gates and offer_ref tool
flow under design/02 §3.7–3.8 and §5.4–5.5. The existing FakeLLM consumes the
code-owned candidate observation, including conditional MOCK wording and cited
selectors; completion and event handlers now reach that path. Required facts
are re-resolved, and lifetime receipts remain the reservation source. Historical
multi-invoice intake stays in Charles's World; engine tests consume its ordinary
cases and ledger balances. Reviewed selected-case routing and cross-kind work
ordering against §3.5, §4.5 and §5.7; the existing adapters retain those behaviors.

Finished owned nonfinancial consumers: explicit legal-review routing and human
escalation, canonical buyer reason/sender/line matching, cited email classification
facts, policy/readiness citation rechecks, both buyer recipient targets, and shared
scan-capability delegation (§3.7, §5.3, §5.8). The harness preserves the actual
human-escalation reason instead of retrying into a generic loop message.

The full demo exposed follow-up defects: a receipt event cancelled an already
scheduled matching due item, initial buyer evidence could cancel a later receipt's
schedule, and approval could no longer validate a scheduler draft after the
pending-only CaseView stopped exposing its completed due item. The scheduler
retains matching schedules, checks reply chronology and recognizes the saved
current draft when revalidating completed due work. Initial demo runs failed at
missing/unsupported follow-up; the new receipt-event regression and final demo
verify the repaired path. Initial authored fixtures also used incorrect Receipt
and clock attributes, an incomplete duplicate deduction, and an incorrect claim
item expectation; these test fixtures were corrected without changing contracts.

Acceptance coverage: tests/engine/test_007_8_integration.py uses app.build and
in-memory SQLite throughout its integration lane. Tests cover authority equality,
below/over limits; missing/conflicting/incomplete/expired/malformed offers and
policy; all three unconfirmed money trusts and confirmation; exact punctuation;
NP exclusion; line/open-balance limits; complete required citations; simultaneous
approved offers; lifetime case and line reservations; over-reservation escalation;
zero line edits with retained keys; positive aggregates; selector replay; stale
approval basis/decision; expiry at approval and submit; duplicate MOCK submission;
immutable receipts and unchanged ledger; new-offer handler idempotency; remittance
invoice balances, unrelated-case isolation and replay; legal inventory/conflicts/
trust; and buyer identity/classification. Existing scoped-controller and event/
due suites remain part of make check. Full H/C/N acceptance exercises day-0
credits/dispute, day-3 correction/incremental credit, follow-up, notice and day-95
claim readiness with blocked submission for the missing statement.

Changed files for this step (all owned):
- recoup/engine/counteroffers.py (new)
- recoup/engine/derive.py
- recoup/engine/gates.py
- recoup/engine/harness.py
- recoup/engine/rules.py
- recoup/engine/scans.py
- recoup/engine/scheduler.py
- recoup/engine/tools.py
- tests/engine/test_007_8_integration.py (new)
- tests/engine/test_rules.py
- tests/engine/test_scan_ingest.py
- progress/sonny/PROGRESS.md

Actual CLI check-regression: r01–r08 PASS (8/8), runtime engine, LLM fake.
Actual doctor: text PDF/Pillow/pdftoppm available; tesseract/pytesseract absent,
vision disabled, no key, no network check. No real OCR, live model or real send
acceptance is claimed. Optional OCR tests remain explicit skips.

Final make check: `make check PYTHON=/tmp/recoup-007-check/bin/python`, exit 0:

```text
All checks passed!
94 files already formatted
================= 1017 passed, 2 skipped in 111.97s (0:01:51) ==================
```

The 48 new acceptance cases execute; the full H/C/N demo and the receipt-event
regression pass. git diff --check passes. The twelve changed files are listed
above; every file is within the handoff ownership, and no other files need reverting.

DONE: Implemented 007-8 counteroffer consumers, shared-intake integration and the cited remaining owned adapters; make check passes (1017 passed, 2 optional OCR skips), full H/C/N demo passes, regression 8/8 passes.
NEXT: Stop after 007-8; leave the twelve owned changed files uncommitted for review.
QUESTION: None for the offline lane; real OCR and live-model evaluation remain unavailable and unclaimed.

## Approved nonfinancial rules verification — 2026-11-09 (America/Los_Angeles)

Applied the user's instruction to use the approved legal-review signal,
buyer-sender classification, escalation and citation-validity rules. Read current
design/02 §3.7 and §5.3 and Charles's SONNY-FINANCIAL-HANDOFF.md and
SONNY-WORLD-HANDOFF.md. Verified publication
933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f is an ancestor of HEAD; shared contracts
and design/02 have no working-tree changes. Existing uncommitted engine changes
already implement these approved decisions; preserved them without rewriting,
staging, committing, or publishing them.

Focused offline verification:
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine/test_007_8_integration.py -k 'legal or buyer_classification' -q`:
  9 passed, 39 deselected. Covers explicit signal routing, authority inventory,
  conflict/untrusted escalation and buyer sender/line classification.
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine/test_007_3_integration.py tests/engine/test_tools_gates_derive.py tests/engine/test_policy_readiness.py tests/world/test_counteroffer_boundary.py -k 'citation or readiness or ungrounded' -q`:
  52 passed, 74 deselected. Includes actual app-built World citation/grounding
  checks and consumer validation in addition to pure readiness checks.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0, Ruff lint and
  formatting PASS, 1017 passed, 2 skipped in 118.93s. The two optional OCR tests
  remain skipped; no paid API, network test, or real send was used.

Updated CONTRACT_REQUEST.md to mark requests 1–4 resolved by the approved
normative decisions, retaining the original requests as history. Their earlier
missing-decision/citation-interface blockers no longer apply. This session edited
only progress/sonny/CONTRACT_REQUEST.md and progress/sonny/PROGRESS.md; all
pre-existing implementation changes remain uncommitted for review.

DONE: Verified the existing implementation uses the four approved rules; focused checks and make check pass; requests 1–4 marked resolved.
NEXT: Stop this verification step; preserve existing uncommitted work for review.
QUESTION: None for these approved rules.

## offer_ref contract and counteroffer acceptance — 2026-11-09 (America/Los_Angeles)

Applied the user's request to include the new selector contract and counteroffer
derivation/gate acceptance. Read Charles's SONNY-FINANCIAL-HANDOFF.md, spec 007-8,
and design/02 §3.7–3.8, §5.4–5.5. Charles publication
`933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f` is an ancestor of HEAD. The existing
`codex/007-4-harness-factory-ingestion` working tree already contains the approved
shared contracts and uncommitted 007-8 engine integration work. Preserved that
work; did not stage, commit, switch branches, edit shared files, or publish it.

Imported Proposal, Approval, Receipt and DraftProposalArgs carry offer_ref with
legacy default None. Added nine explicit app-built in-memory acceptance cases in
`tests/engine/test_offer_ref_acceptance.py` covering all four imported records'
JSON compatibility, exact selector preservation, approval/receipt version binding,
URL-encoded identity, code-owned allocations, positive gate acceptance at save /
approve / submit, downward edits, rejected increases, selector rebinding, and
selectors rejected on ordinary proposal kinds. No local contract models or
model-supplied amount inputs were introduced.

Review found a derivation gap against design/02 §5.4: different active complete
emails with the same offer reference and different allowed senders were accepted.
The new regression failed before the repair: **1 failed, 8 passed in 2.70s**.
Updated only the sender-consistency check in the existing counteroffers.py so
repeated offers must agree on sender. Equal repeated sources still yield one
concession. The same regression checks rejection through the engine validator at
all three stages. After repair the new module reports **9 passed in 2.60s**.

Focused acceptance command:
`RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m pytest tests/engine/test_offer_ref_acceptance.py tests/engine/test_007_8_integration.py tests/world/test_counteroffer_boundary.py -q`
reported **79 passed in 92.68s** before the two additional repeated-source cases
were added. It verifies the existing counteroffer derivation/gate path, boundary,
source/trust, lifetime reservations, edits, stale approvals, competing offers,
duplicate submission, selector replay and actual World defenses. The final full
suite below includes all nine new cases and the sender repair.

Marked historical contract request 7 resolved against the published definitions.
No additional contract change is needed. This session's changed files are:
- recoup/engine/counteroffers.py (small repair to existing uncommitted implementation)
- tests/engine/test_offer_ref_acceptance.py (new)
- progress/sonny/CONTRACT_REQUEST.md
- progress/sonny/PROGRESS.md

Other pre-existing changed/untracked files are preserved; they are not changes
introduced by this verification/repair. Shared contracts and design/02 remain
unchanged (`git diff --exit-code -- recoup/contracts docs/design/02-technical-design.md`:
exit 0). `git diff --check` passes. No network, model spend or real send was used.

Final verification: `make check PYTHON=/tmp/recoup-007-check/bin/python`, exit 0;
Ruff lint PASS; format PASS (95 files); **1026 passed, 2 skipped in 114.74s**.
The two unavailable optional OCR paths remain explicit skips; live-model and real
send acceptance are not claimed. All new selector/counteroffer cases execute on
actual app-built SQLite. A separately introduced untracked
`tests/engine/test_counteroffer_harness.py` appeared during verification; it was
not edited or included in this session's claimed test count. Existing work remains
uncommitted for review.

DONE: Included imported offer_ref compatibility/binding and derivation/gate acceptance; repaired conflicting offer senders; nine new cases and make check pass.
NEXT: Stop this acceptance step; preserve all existing uncommitted work for review.
QUESTION: None for the approved offer_ref/counteroffer offline acceptance.

## Counteroffer harness coverage — 2026-11-09 (America/Los_Angeles)

User-requested follow-through for counteroffer tool selection, completion,
FakeLLM coverage and selected-case execution. Preserved all existing uncommitted
implementation and tests. Existing engine behavior already handles these cases;
this follow-through changes only `tests/engine/test_counteroffer_harness.py` and
appends this progress entry. Business definitions: design/02 §4.5, §5.4–5.6.

Five new real app-built SQLite checks (no doubles for World):
- FakeLLM selects opaque `A/B` and D2 through `draft_proposal`, supplies no
  money/allocations, requests approval, and ends without auto-approval or receipt.
- Completion refuses `end` when only the counteroffer remains; accepts its draft
  and subsequently its MOCK receipt. Submission leaves the ledger unchanged.
- Default app `run(case_id)` drafts the selected case's offer without touching
  another loaded case's history, pending events, due work or decision.
- Expired and over-authority offers do not block ordinary work or completion
  (two parametrized cases).

Commands/results:
- `python -m pytest tests/engine/test_counteroffer_harness.py -q` using existing
  `/tmp/recoup-007-check/bin/python`: **5 passed in 1.16s**.
- Existing counteroffer integration and offer-ref acceptance modules:
  **57 passed in 95.37s**.
- `git diff --check`: PASS, including preserved existing changes.
- `make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint/format PASS;
  **1031 passed, 2 skipped in 116.07s**. The two existing scan capability skips
  remain; the five new real integration tests all ran and passed.

DONE: Added five passing counteroffer harness/completion/FakeLLM/selected-case tests; full make check passes. Changed files: tests/engine/test_counteroffer_harness.py and progress/sonny/PROGRESS.md only in this follow-through.
NEXT: Stop; leave all existing implementation edits intact and uncommitted.
QUESTION: None for this coverage request.

## 007-5 approved ordering and buyer allowlists — 2026-11-09

Applied the published design/02 §5.7 ordering directly in the scheduler and
replaced the obsolete fallback comment with its normative reference. Request #5
is now marked resolved against that approval. Sender membership uses the union
required by design/02 §3.7; the existing uncommitted two-allowlist behavior was
preserved and expressed explicitly as a set union. No contract edits are needed.

Added seven cases in tests/engine/test_007_5_integration.py against the actual
app-built SqliteWorld(":memory:"). `test_real_event_due_ordering` reverses the
provider lists, checks both ranks' tie behavior and chronological precedence,
leaves future work pending, and verifies a second handle adds nothing. Its engine
investigation callback is inert to isolate scheduling, while all persisted work,
events, transactions and acknowledgements use the real World.
`test_real_reply_allowlists` has six cases: distinct email-only and portal-only
senders plus an ERP-only negative control, both through the email event path and
through the due handler's active-evidence suppression path after decision refresh.

Initial new integration assertions had seven fixture failures: CaseView exposes
pending due work only, loading emits multiple initial events, and adding evidence
invalidates the decision. Corrected the tests to observe real acknowledgements,
include all initial events, and explicitly refresh the decision when bypassing
its email event. No production behavior was weakened to satisfy those fixtures.
Focused integration command: `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m
pytest tests/engine/test_007_5_integration.py -q`: **12 passed in 13.12s**, no skips.

Files changed in this follow-up only:
- recoup/engine/scheduler.py
- tests/engine/test_007_5_integration.py
- progress/sonny/CONTRACT_REQUEST.md
- progress/sonny/PROGRESS.md

All other pre-existing modified and untracked files were preserved. No network,
real send, dependency installation, shared contract edit, commit or publication.

Final `make check PYTHON=/tmp/recoup-007-check/bin/python`: exit 0; Ruff lint and
format PASS (96 files); **1038 passed, 2 skipped in 125.13s**. The optional OCR
skips remain; all scheduler integration cases executed. `git diff --check` passed.

DONE: Used approved scheduler ordering, verified both buyer sender allowlists on actual SQLite, resolved request #5, and passed make check.
NEXT: Stop this follow-up; preserve unrelated in-progress work and leave changes uncommitted for review.
QUESTION: None for the approved ordering or email/portal sender recognition.

## Shared capability reporting — 2026-11-09 (America/Los_Angeles)

User requested delegation to contracts.capabilities.scan_capabilities (design/02
§5.8). On entry, scans.py already imported the shared probe and its existing tests
already patched the shared module. Preserved those edits and all other existing
uncommitted work. Updated factory.py to import the shared probe directly.
No shared contract files, dependencies or extraction behavior changed.

Verification: make check PYTHON=/tmp/recoup-007-check/bin/python passed Ruff lint,
format (96 files), and pytest: 1038 passed, 2 skipped in 124.12s. The two existing
real OCR skips remain. git diff --check passed.

DONE: Engine capability reporting delegates to the shared contract probe; full checks pass. Files changed in this follow-through: recoup/engine/factory.py and progress/sonny/PROGRESS.md.
NEXT: Stop; preserve existing uncommitted changes for review.
QUESTION: None.

## Session handoff and Git publication — 2026-11-09 (America/Los_Angeles)

User requested updating the session handoff and pushing the accumulated changes.
Added [SESSION-HANDOFF.md](SESSION-HANDOFF.md) as the current consolidated status,
including the complete 18-file publication list, shared candidate pins, acceptance
scope and reviewer/verifier next step. Earlier instructions to leave this work
uncommitted are superseded by this publication request. No implementation was
changed in this publication step; all existing owned engine and test edits are
included. No shared contracts or other protected files changed.

Fresh verification: `make check PYTHON=/tmp/recoup-007-check/bin/python` exits 0:
Ruff lint PASS, 96 files formatted, **1038 passed, 2 skipped in 116.15s**.
The two existing optional OCR skips remain. Actual fake-LLM in-memory CLI
`check-regression` passes r01–r08 (8/8). `git diff --check` passes.
Fetched origin before publication; the current branch has two existing commits
ahead and none behind its remote. Publication uses the existing
`codex/007-4-harness-factory-ingestion` branch without a force push.

DONE: Updated the session handoff and prepared all 18 owned files for the user-requested commit/push; fresh make check and regression 8/8 pass.
NEXT: Push this publication commit, verify remote equality and a clean working tree, then stop for reviewer/verifier review.
QUESTION: None for this publication; real OCR and live-model acceptance remain unclaimed.

DONE: 2026-11-09 live-adapter hardening (design/02 §5.1–5.2, §5.9): malformed batches, text-only responses, optional usage, safe provider/recording failures, zero provider retries and remaining-wall timeout; offline fake-HTTP tests use in-memory SqliteWorld. Official SDK tool-calling documentation read 2026-11-09: https://developers.openai.com/api/docs/guides/function-calling . make check PYTHON=/tmp/recoup-007-check/bin/python PASS (1134 passed, 2 optional OCR skips); changed recoup/engine/harness.py, recoup/engine/llm/{errors,openai_compat}.py, tests/engine/{test_live_failures,test_openai_compat}.py and this progress log.
NEXT: Stop after this step. Clean H/C/N recoup run attempts all stopped on Groq HTTP 429 without retry or verdicts; genuine H=2/C=1 response prefixes in runs/recordings matched network-blocked CLI replay exactly (calls, arguments, text, tool results), N=0. Full completion, oracle verdict comparison and full replay remain unverified; replay stops at missing failure-response recordings. Evidence: runs/live-hardening-w5b_m_py/verification.json. Earlier H from fake-populated CLI-load state stopped HTTP 413 and is excluded from clean-case verdict evidence; its one genuine response was also replayed exactly.
QUESTION: No code question; a later authorized live verification needs available Groq quota. Credentials were passed from macOS launch environment directly to child processes without printing or saving them; no dependency, contract, fixture or oracle edits.

## Queued investigation diagnosis — 2026-11-10 (America/Los_Angeles)

User-authorized one-step engine handoff: `recoup/engine/scheduler.py`,
`tests/engine/test_scheduler_reinvestigation.py`, and this log. Read root/engine
AGENTS, specs/007, design/01, design/02 §2, §4.4–4.5, §5.1–5.2, §5.6–5.10,
Sonny's session handoff, and Carter's shared-backend handoff/progress. Existing
uncommitted adapter/harness/UI/deployment work is preserved.

Read-only production inspection via the Vercel Sandbox skill: launcher deployment
`dpl_3JJcHMemRNsS1Pe72qcLk3KY15Sb` is READY; current named Sandbox session
`sbx_RlF65jLsUboRjifZEd2mbhyqOSae` is running and backend health returns 200.
All 101 model-call traces match their exact request-keyed recording JSON, with
zero missing/mismatched files; all report live `claude-haiku-5-5`. Zero approvals
and receipts. Production fixture/recorder SHA-256 values match local sources.
No provider requests, secret reads, production case writes, or deployment edits.

Actual stops: H/N report recording unavailable/conflicting, unmet=[]; C reports
loop, unmet=[]. H's current first request hashes to
`e625f16cb694077a01640755e66177e36e40db62045305810ddd97061048376d`, N's to
`3b78c491684f1a21081fbb7cda7e2210bd6a840c5d3ad52849efb3361474363f`;
both recording files exist. Reconstructed requests used only an app-built
in-memory backup of the read-only production DB, without agent execution.
The recorder compares entire serialized responses including latency. Rejected
responses were not retained, so metadata-only versus substantive differences
cannot be determined from the saved artifacts. C's final model turn 3 repeats
`readiness(kind=dispute,line_id=D1)` after propose_decision; tool steps 8 and 10
have identical args/results. Its missing dispute finding is consistent with a
valid credit-only line, not missing case information. Repeated scheduler events
continued after earlier accepted ends: H=12 events/6 accepted ends/34 model calls;
C=10/2/44; N=6/4/23. These counts substantiate redundant investigation, not a
provider outage or a need for invented human-input files.

Evidence-backed product recommendation (unchanged rules; design/02 §5.3–5.6):
H disputes D1 312000 cents: EV-H-BOL-v1 fields.shipped.SKU-1=400,
EV-H-POD-v1 fields.signed=true and fields.received.SKU-1=400;
EV-H-REM-v1 fields.ded.1.qty=40/claimed_cents=312000, and EV-H-TERMS-v1
fields.price.SKU-1_cents=7800. H credits D2 180000/disputes 132000 cents:
EV-H-TERMS-v1 fields.promo.FALL26.earned=true/cap_cents=180000 versus
EV-H-REM-v1 fields.ded.2.claimed_cents=312000. C credits 50000 cents:
EV-C-PRICE%2DAMENDMENT-v1 fields.authority_role="VP Sales",
fields.effective_date="2026-08-15", fields.price.SKU-7_cents=1000;
EV-C-COMPANY-v1 fields.allowed_authority_roles="VP Sales,Finance Director";
EV-C-INV-v1 fields.invoice_date="2026-09-01", fields.line.1.qty=1000 and
fields.line.1.unit_price_cents=1050. N's 215000-cent difference is unexplained:
EV-N-INV-v1 fields.total_cents=2000000 versus EV-N-PAY-v1 fields.paid_cents=1785000.
Request a remittance/debit memo specifying the deduction reason and supporting
line-level evidence; do not assert either a valid concession or a dispute.
All outward drafts/book changes retain explicit approval-bound MOCK submission.

Decision: reuse an accepted investigation only within the same chronological
scheduler drain when the entire CaseView, FactSet, ledger and recipient lists
match. Trace every reused event with its source event id, acknowledge it in its
own transaction, and retain scheduling/buyer-reply handling. Failed/budget/loop
runs are never cached; due work and explicit investigations execute normally.
No recording comparison, loop guard, contract, fixture, model fallback, money
calculation, approval requirement or dependency was changed. Existing production
needs_human records are preserved; this local patch is not deployed and no new
live-model completion or complete live replay is claimed.

DONE: 2026-11-10 one-step scheduler reuse of accepted investigations for unchanged queued case state (design/02 §4.5, §5.2, §5.7–5.9); production causes/recording fidelity and evidence-backed H/C/N recommendations inspected above. make check PYTHON=/tmp/recoup-007-check/bin/python PASS: Ruff lint/format, 1154 passed, 2 existing optional OCR skips in 160.54s; focused scheduler suite 35 passed. Changed only recoup/engine/scheduler.py, tests/engine/test_scheduler_reinvestigation.py and progress/sonny/PROGRESS.md; prior uncommitted work preserved.
NEXT: Stop after this implementation step. Local patch is ready for review; production still runs its existing source and retains its original needs_human records. A future rollout/live run must verify model completion without rewriting historical traces, recordings or statuses.
QUESTION: None; no credential, protected-file change, dependency or irreversible action was required.

DONE: Prepared the user-requested Git publication of the queued-investigation fix and its regression tests; previous make check passed (1154 passed, 2 optional OCR skips).
NEXT: Push the focused commit to origin/sonny/live-model, verify remote equality, and stop; leave other uncommitted work untouched.
QUESTION: None.

DONE: 2026-11-10 single unseen-case step ALDER-2718: source-only SYNTHETIC fixture, evaluator-only checklist, app-built offline/in-memory validation and make check PASS (1156 passed, 2 optional OCR skips). Actual deployed Haiku claude-haiku-5-5 first load: 18 model calls, 68 tool calls, three proposals, two accepted ends; early loop and stale needs_human status preserved. Separate React-default DB load failed with ValueError: Conflicting replay recording; no fallback or recording edits. Saved original live draft is expanded in React via Open saved run. No approvals, receipts or changes to existing case histories. Every changed file is listed in progress/sonny/unseen-alder-2718/CHANGED-FILES.md.
NEXT: Stop after this case-generation/evaluation step. Human reviews the three saved proposal versions and obtains the missing broth inspection/quantity; any harness/status or recorder fix requires a separate handoff.
QUESTION: None blocking this evaluation; stale status after accepted end, dispute-readiness misuse and repeated-request recording conflict remain documented defects, not repaired or concealed.

DONE: 2026-11-10 user-requested publication of all pending changes. make check PYTHON=/tmp/recoup-007-check/bin/python PASS: Ruff lint/format, 1156 passed, 2 optional OCR skips; Node launcher tests 5 passed. Changed files are enumerated by the publication commit manifest.
NEXT: Push the publication commit to origin/sonny/live-model, verify remote equality and a clean working tree, then stop.
QUESTION: None.
DONE: 2026-11-10 added exactly two SYNTHETIC USD demos: PAID-FULL (125000 invoice/payment) and PAID-INSTALLMENTS (240000 invoice; 90000/150000 payments), distinct source references, normal directory demo loading via app.build/intake/rules/FakeLLM. App-built in-memory SQLite and UI acceptance verify zero balances, no U1/NP, empty findings/decisions, no proposals/actions/due work, repeat-load state idempotency and preserved H/C/N behavior; make check PYTHON=/tmp/recoup-007-check/bin/python PASS (Ruff lint/format; 1167 passed, 2 optional OCR skips). Exact changed files: README.md; cases/demo/PAID-FULL/bundle.json; cases/demo/PAID-INSTALLMENTS/bundle.json; recoup/ui/workbench.py; tests/app/test_paid_demo.py; tests/ui/test_workbench.py; tests/world/test_fixtures.py; progress/sonny/PAID-DEMO-HANDOFF.md; progress/sonny/PROGRESS.md. Normative refs: design/02 §3.7, §4.5, §5.3–5.9; no protected files, rules, dependencies, live provider or deployment changed/exercised.
NEXT: Stop after this implementation step; review the nine allowlisted files. FakeLLM verifies offline tool behavior, not live model judgment.
QUESTION: None. Repeat loading may add agent/audit traces under existing orchestration; evidence, ledger, saved decisions, proposals, receipts and due state remain idempotent.
DONE: 2026-11-10 prepared all nine pending paid-demo files for user-requested Git publication; make check PYTHON=/tmp/recoup-007-check/bin/python PASS (Ruff lint/format; 1167 passed, 2 skipped). Files: README.md; cases/demo/PAID-FULL/bundle.json; cases/demo/PAID-INSTALLMENTS/bundle.json; recoup/ui/workbench.py; tests/app/test_paid_demo.py; tests/ui/test_workbench.py; tests/world/test_fixtures.py; progress/sonny/PAID-DEMO-HANDOFF.md; progress/sonny/PROGRESS.md.
NEXT: Commit and push to origin/sonny/live-model, verify remote equality and clean working tree, then stop.
QUESTION: None.
