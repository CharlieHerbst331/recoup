# 006-4 fixture acceptance — 2026-11-08

Candidate contract: `89675c0b6ac676fa28c3475f58134689b74c274c`.
Observed checkout: branch `006-2b-sqlite-world-core-and-app-build`, HEAD
`a27ad5b8d0290041f86aefc40602cde6b2ac1afa`. Candidate ancestry and unchanged
contract checks passed. Work is uncommitted and shares this checkout with the
user-authorized 006-2B/006-3/006-5 work; no checkout, commit, tag, merge or send
was performed by this fixture task.

All data is SYNTHETIC. The policies are fixture terms, not insurance advice.
Business semantics are defined in design/01 §10 and design/02 §3.3, §3.7,
§5.3–5.6 and §8.1. The external r10 design/04 §2–4 authorizes independent
fixture schema tests and requires separate real-loader/engine acceptance.

| Fixture | Coverage |
| --- | --- |
| demo/H | Hero invoice, shortage, capped FALL26 promotion, day-3 POD v2 and inspection; missing statement |
| demo/C | Authorized VP Sales pricing amendment carried by email |
| demo/N | Unexplained short payment |
| regression/r01 | Early payment; pricing with unauthorized amendment |
| regression/r02 | Late delivery; authorized return |
| regression/r03 | Unsigned POD shortage; needs information |
| regression/r04 | Late-reported damage; waiver term absent; needs information |
| regression/r05 | Partial promotion deduction |
| regression/r06 | Unexplained short payment; no dispute |
| regression/r07 | P-B nonpayment; balance above credit limit; fixed claim item ids |
| regression/r08 | EUR quarantine |

Independent validation: PASS. `python -m pytest tests/world/test_fixtures.py -q`
via `.venv/bin/python`: **48 passed** (36 fixture checks and 12 real-loader
checks). Inputs and oracles use the actual shared Pydantic models; raw cents
are integers, invoice/remittance amounts reconcile, field keys use the
published vocabulary, evidence refs resolve to fixture docs/fields, and all
nine reasons are represented. Acceptable refs include full proof dependencies.
The two reusable policy BundleDocs match their embedded copies exactly.

Real loader integration: PASS against `SqliteWorld(":memory:",
TextOnlyIngestor(), PassValidator())`. All 11 bundles load or quarantine as
specified; loaded evidence, ledger balances and deduction line ids match the
fixtures. EUR creates no CaseView, evidence or ledger rows. H exposes day 3
as the next due boundary; calendar-only advance preserves the original
active evidence and holds the future documents.

Full check: `make check` PASS, **304 tests passed**, ruff lint and formatting
passed. An initial fixture test incorrectly requested a normal history for a
quarantined case; corrected the assertion to verify no evidence/ledger rows.
No failing tests remain at this validation snapshot.

Actual engine/financial acceptance: BLOCKED on Sonny's real rules, readiness,
factory and harness. The contract stub cannot verify oracle verdicts,
unsupported-terms basis, proposed amounts, corrections or claim readiness.
PassValidator only validates loader behavior here. In particular, missing-item
strings in r03/r04 and the pre-notice r07 checklist need actual-engine replay;
no unit pass is claimed as G3 acceptance. Full automatic day-3 event release
and correction/credit flow require 006-3 and the real engine. Holdout was not
created, read or modified.

Changed files (fixture task only):

- `cases/policies/P-A.json`
- `cases/policies/P-B.json`
- `cases/demo/H/bundle.json`
- `cases/demo/C/bundle.json`
- `cases/demo/N/bundle.json`
- `cases/regression/r01/bundle.json`
- `cases/regression/r01/oracle.json`
- `cases/regression/r02/bundle.json`
- `cases/regression/r02/oracle.json`
- `cases/regression/r03/bundle.json`
- `cases/regression/r03/oracle.json`
- `cases/regression/r04/bundle.json`
- `cases/regression/r04/oracle.json`
- `cases/regression/r05/bundle.json`
- `cases/regression/r05/oracle.json`
- `cases/regression/r06/bundle.json`
- `cases/regression/r06/oracle.json`
- `cases/regression/r07/bundle.json`
- `cases/regression/r07/oracle.json`
- `cases/regression/r08/bundle.json`
- `cases/regression/r08/oracle.json`
- `tests/world/test_fixtures.py`
- `progress/charles/006-4-ACCEPTANCE.md`

The root coordinator owns the shared `progress/charles/PROGRESS.md` append.
