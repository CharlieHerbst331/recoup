# Charles final branch integration — 2026-11-09

Sonny's published `e12fef4266c6339c5baa9f148e9e1d6558b66e2b` was fetched and fast-forwarded into
`006-2b-sqlite-world-core-and-app-build` from Charles's `933ab05` publication.
It includes the actual 007-8 counteroffer implementation and the remaining
approved shared-seam consumers. The shared contract tree remains
`fb064458d4070d7290bd0f242a28d56f1c31aac7`; Sonny changed only his owned paths.

This report supersedes the historical absent-engine, repeated-decision,
claim-item identity and unimplemented-counteroffer blockers in earlier Charles
audits. The older records are preserved. There is no extra 006-6 implementation
step: this completes 006-5's actual provider integration and final offline
acceptance lane. Carter does not block this offline branch integration.

## Verified integration

- Initial unmodified Sonny tree `make check`: clean lint/format; **1038 passed,
  2 optional OCR skips**.
- Actual installed engine `recoup --db :memory: check-regression`: **8/8 PASS**.
- The added persisted CLI test uses actual engine factories and financial gates,
  with a reopened SQLite database for every command. It verifies day-zero credit,
  edited dispute approval/receipt/replay, day-three automatic reconsideration,
  linked correction and incremental credit, immutable original receipt and no
  duplicate economic effect.
- Public-facade H/C/N and financial acceptance is detailed in
  [006-FINAL-DEMO-ACCEPTANCE.md](006-FINAL-DEMO-ACCEPTANCE.md). This includes the
  actual counteroffer receipt and shared multi-invoice remittance consumer.
- Read-only subagent review checked the shared definitions against financial
  derivation, approval/receipt reservations, sender and legal classification,
  current citation checks, event/due ordering and the shared scan probe.

## Resolved final review finding: human escalation

A model can request `propose_decision` before `run_rules`. In the published
engine, the harness's rule-based verdict override calls `run_rules` before the
tool error handler. `NeedsHumanError` then escapes for missing/unreadable legal
authority or a negative deduction. A scoped app run rolls back instead of
preserving a `needs_human` case with the reason. The financial gates do not allow
a mock action, but the required human-routing state is lost.

`tests/app/test_human_escalation_acceptance.py` reproduces all three cases through
the actual assembled app and ScriptedLLM, without importing engine internals.
All three failed on Sonny's published source. The reviewable
`SONNY-FINAL-ENGINE-FIX.patch` catches that exception around the override and
uses the existing harness stop path. The user explicitly approved applying the
engine fix in this chat, overriding the Charles handoff's engine ownership
restriction for this change. The exact patch is now applied to
`recoup/engine/harness.py`; all three actual-app acceptance cases pass on disk.
The error is preserved as a human-routing reason, with no decision, receipt or
ledger change. No other engine source was edited by Charles.

## Remaining limits

- Formal gates in design/02 §2 mean PRs merged on main. Branch tests and these
  internal reviews do not imply those merges, independent Reviewer/Verifier
  sign-off, or a `contract-v1` tag. Main was not merged or changed.
- Tesseract is absent; the two optional OCR tests skip. Doctor detects pypdf,
  Pillow, pytesseract and pdftoppm, but reports OCR and vision unavailable here.
  No software was installed and no live-model spend or external send occurred.
- UI/benchmark implementation, opaque holdout custody and live/recorded proof
  remain separate work. They are not prerequisites for Charles's offline CLI.
- The insurer summary badge remains `claim_waiting` at day 95 although the
  current readiness checklist correctly says `not_ready` and blocks submission.
  The existing normative scheduler specifies investigation at the claim window
  but no complete badge transition policy. This presentation limitation is
  recorded without inventing an eligibility claim or changing financial gates.
- Valid legacy data remains supported. Historical FactSets predating the sender
  metadata default to an empty allowlist. Legacy uncited fact revisions require
  an explicit migration; no automatic data repair is included.

## Changed files and final checks

Before applying the approved fix, `make check`: lint/format PASS; **1044 passed, 3 failed,
2 optional OCR skips** in 208.84 seconds. All three failures are the new human
escalation acceptance cases above. The full facade demo and persisted CLI cases
passed. That failed acceptance exposed the bug; it is retained as historical
evidence.

**Final post-fix `make check`: lint/format PASS; 1047 passed, 2 optional OCR skips
in 213.74 seconds.** The targeted three escalation cases also pass independently
on disk, and the post-fix actual-engine regression command passes **8/8**.

The tested implementation SHA is
`97ded2c34a6215511b97fa5910d3251c1ca12521`. The shared contract tree is unchanged.
All 13 paths below are published
on `006-2b-sqlite-world-core-and-app-build`; subsequent record changes affect
documentation only. Original untracked `arhcive/` and
`recoup-006-charles-bundle-r10.md` remain untouched and excluded.

Complete Charles change list:

- `README.md`
- `cases/ambition/README.md`
- `docs/INDEX.md`
- `docs/design/01-functional-design.md`
- `docs/design/02-technical-design.md`
- `progress/charles/006-FINAL-DEMO-ACCEPTANCE.md`
- `progress/charles/006-FINAL-INTEGRATION-ACCEPTANCE.md`
- `progress/charles/PROGRESS.md`
- `progress/charles/SONNY-FINAL-ENGINE-FIX.patch`
- `recoup/engine/harness.py`
- `tests/app/test_final_integration.py`
- `tests/app/test_human_escalation_acceptance.py`
- `tests/cli/test_engine_workflows.py`
