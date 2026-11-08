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
