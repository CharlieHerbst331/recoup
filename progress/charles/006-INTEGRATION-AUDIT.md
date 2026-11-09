# Published engine integration audit — 2026-11-08 PT

The user asked whether Sonny's implementation unblocks the prior Charles work.
`git fetch origin` discovered `origin/codex/007-4-harness-factory-ingestion` at
`d41c283aaef382103ce0d364047c11391b8470ff`. It contains 007-1 rules, 007-2
policy/readiness, 007-3 tools/validator/derivation, 007-4 harness/factory/ingestion,
007-5 scheduler, 007-6 SDK adapter, and 007-7 optional scan support. Sonny's 007-8
ambitions remain explicitly unimplemented pending definitions. Shared contracts
are byte-identical to candidate `89675c0b6ac676fa28c3475f58134689b74c274c`.

The missing-engine-provider blocker is removed at the published-tree level.
The feature branch is not merged into main or this checkout. No merge, push,
tag, external message, live request, dependency installation or shared-contract
change was performed. `origin/main` separately records owner acceptance of F0
in `fc425ce362bc71fad6afc584e854edfd21e9b3fe`; that record says independent
Reviewer/Verifier reviews were not performed and no contract-v1 tag was created.
This supersedes the old F0-pending status as an observed owner record.

The initial Charles tip was `d954dbbf75bc49465919bec2d846c40af104cd77`.
For compatibility verification, a temporary directory contains an exact export
of that tip plus Sonny's published `recoup/engine`, `tests/engine` and
`progress/sonny` trees. Only Charles-owned fixes/tests/fixture expectations were
subsequently copied into that temporary snapshot. This tests actual source
providers without merging or editing Sonny's files. PYTHONPATH points to the
snapshot, RECOUP_LLM=fake, API keys are removed, and the existing virtualenv
runs the unchanged Makefile. The initial runner mistakenly resolved the venv
Python symlink to a global interpreter without ruff; rerunning with the venv's
absolute, unresolved path corrected that test-runner error.

## Results

| Check | Actual result | Meaning |
| --- | --- | --- |
| Initial combined make check | 851 passed, 16 failed, 2 skipped | Not integrated acceptance |
| Initial Sonny real-provider acceptance modules | 16 passed, 7 failed | Previously blocked integration cases actually ran |
| New World boundary regressions before/after fix | 10 failed/1 passed -> 11 passed | Demonstrates fixes, not merely new green tests |
| Final current-checkout make check | 450 passed, 3 skipped; lint/format PASS | Engine remains absent from this unmerged checkout |
| Final combined make check | **874 passed, 7 failed, 2 skipped**; lint/format PASS | Actual integration is still FAIL |
| Actual combined regression gate | **7/8 PASS**; r07 FAIL | Full G3 gate still fails |
| Shared contracts, dependencies, Makefile, AGENTS diff | Empty | No silent candidate/dependency drift |

The three current-checkout skips are individually named real-engine acceptance:
`test_real_hero_has_current_approvable_proposals`,
`test_real_concede_demo_has_only_supported_credit`, and
`test_real_unexplained_demo_requests_information_without_loop`. They all run and
fail in the combined snapshot. They are BLOCKED locally, never counted as PASS.
The combined snapshot's only skips are optional real tesseract image/scanned-PDF
OCR tests; tesseract is unavailable. No live/OCR accuracy claim is made.

## Charles changes completed

- Normalize status/insurance values through existing contract enums at the World
  boundary, validating before writes. Sonny's string values no longer raise
  AttributeError; invalid strings roll back without partial state updates.
- Fact-change events reference the owning Evidence id, which the actual scheduler
  resolves; the fact revision id remains in the cascade trace. Citation-free line
  reasons reference real source or ledger-backed evidence. In an incomplete DB
  without any backing evidence, retain the explicit trace without fabricating an
  Evidence reference. No new event type or shared model was introduced.
- G1 controller/CLI tests explicitly select their documented contract-stub lane,
  so fabricated orchestration-only decisions do not claim actual-validator
  acceptance. Actual engine tests run separately without that fixture.
- Added actual H/C/N approval acceptance checks, exposing stale live proposals.
- Aligned fixture expectations explicitly left provisional in 006-4: r01 D1 may
  cite the unauthorized amendment's author/role as authorization provenance;
  required base proof refs and all verdicts/cents remain unchanged. r03 names its
  missing signed POD using the engine's public `signed POD` vocabulary. r07's
  waiting period is `unknown` before any notice receipt supplies an opening date,
  while notice-receipt absence remains `missing`. No monetary outcome, forbidden
  action, required evidence reference, or claim-document identifier was relaxed.

## Remaining blockers

1. **Repeated engine investigation leaves proposals bound to an old decision.**
   At unchanged evidence hash, each initial evidence/case event invokes
   investigation, creating a fresh decision. An integration hero has nine initial
   events and ends at decision v9 while dispute/credit proposals remain bound to
   v1. The H demo ends at v12 with its live proposals still bound to v1. Current
   decision checks therefore correctly reject approval as `stale_decision`.
   A direct second investigation without an evidence change reproduces it too.
   World proposal no-op follows design/02 §3.8; do not bypass approval/currentness
   checks or mutate approved versions to make this pass. Sonny's engine should
   retain an equivalent current decision or avoid unnecessary replacement while
   preserving real evidence-change versioning and scheduler acknowledgement.

   All seven final combined failures are manifestations of this issue:

   - tests/app/test_engine_acceptance.py::test_real_hero_has_current_approvable_proposals
   - tests/app/test_engine_acceptance.py::test_real_concede_demo_has_only_supported_credit
   - tests/app/test_engine_acceptance.py::test_real_unexplained_demo_requests_information_without_loop
   - tests/engine/test_007_5_integration.py::test_real_day_three_correction_credit_no_repost
   - tests/engine/test_007_5_integration.py::test_real_silence_and_reply[False]
   - tests/engine/test_007_5_integration.py::test_real_silence_and_reply[True]
   - tests/engine/test_007_5_integration.py::test_real_notice_and_claim_dates

2. **Claim checklist document IDs do not preserve the policy's keys.**
   Regression r07 uses `claim_doc.1` through `.4`; design/02 §5.6 and its oracle
   require `claim.doc.1` through `.4`. The actual engine readiness function emits
   `claim.doc.invoice`, `.pod`, `.contract`, `.statement`, so r07 fails
   claim_items. Fix the engine readiness adapter; retain the policy key rather
   than mapping identity to the kind (which can also collapse repeated kinds).

3. The existing selected-case Controller.react contract request remains open.
   The real HarnessController iterates all cases when given an empty event list.
   Doctor/scan-composition and cross-kind due ordering requests also remain in
   Sonny's published CONTRACT_REQUEST; this audit does not invent new shared
   signatures or approve 007-8 financial definitions.

The first two blockers are now actionable Sonny engine changes rather than
missing-provider guesses. Ownership rules prohibit editing those paths in this
Charles task. No integrated gate/merge is claimed.

## Reproduction evidence

Temporary snapshot metadata: `/tmp/recoup-integration-audit-current.json`.
Snapshot at this verification:
`/var/folders/q5/zfc6xw2j6c7_p0ns5tk0vw8c0000gn/T/recoup-integration-audit-j4x6kju6`.
Logs there: `audit-make-check.log`, `audit-real-integration.log`,
`audit-final-make-check.log`, `audit-regression-final.log`.
The independent repeated-investigation diagnostic is
`/tmp/recoup-integration-review-diagnostic.log`. These temporary paths may later
expire; exact source SHAs, counts, tests and failure mechanisms are preserved here.

## Every changed file in this follow-up

- `recoup/world/store.py`
- `tests/world/test_engine_boundary.py`
- `tests/app/test_build_integration.py`
- `tests/app/test_mutations_integration.py`
- `tests/app/test_engine_acceptance.py`
- `tests/cli/test_sqlite_workflows.py`
- `cases/regression/r01/oracle.json`
- `cases/regression/r03/oracle.json`
- `cases/regression/r07/oracle.json`
- `progress/charles/006-INTEGRATION-WORLD-ACCEPTANCE.md`
- `progress/charles/006-INTEGRATION-AUDIT.md`
- `progress/charles/PROGRESS.md`
