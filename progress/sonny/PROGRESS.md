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
