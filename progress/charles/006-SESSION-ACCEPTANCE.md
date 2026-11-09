# Charles 006 enabled-work session — 2026-11-08 PT

The user explicitly authorized subagents and continuation across enabled steps,
starting with 006-2B until outside help is required. That instruction overrides
the handoff's one-step/single-agent stop wording. The requested home-path bundle
was absent; its identical-named input in the repository root was read. Original
untracked `arhcive/` and `recoup-006-charles-bundle-r10.md` remain untouched.

Branch: `006-2b-sqlite-world-core-and-app-build`. Candidate contract:
`89675c0b6ac676fa28c3475f58134689b74c274c`. Required owned 006-2A tip:
`e26f4d13303db628b9a0eddd3ef99fcb65bc9c31`. The checkout began at
`a27ad5b8d0290041f86aefc40602cde6b2ac1afa`. Fetch and candidate/predecessor
ancestry checks passed. No reset, destructive rebase, shared contract change,
dependency change, merge, push, tag, real send or API spend occurred.

Implementation checkpoints:

- 006-2B: `eff1399c6bb662fdde7a86f3abdfb44df56435ed` — actual SQLite core and app build.
- 006-4: `40ba8a8a57c51237bd1683866da798caa0e95b98` — policies, demos and eight regressions.
- 006-3: `5746ad58bd2d4935969f023e9a03bdfcba306050` — transactions, mock actions, cascade and events.
- 006-5: CLI/composition/regression unit lane completed in this session; final
  implementation tip is recorded in PROGRESS.md after its commit.

| Acceptance | Actual provider / evidence | Result |
| --- | --- | --- |
| SQLite persistence, quarantine, evidence/fact versions and historical bases | Real SqliteWorld, core tests and app.build integration | PASS |
| Mock submit ordering, approval bindings, replay, credit/correction guards, rollback and restart | Real SQLite with explicit validator/ingestor stubs, World action tests | PASS |
| Future evidence, held fetches, day-3 H release, due work and event acknowledgement | Real SQLite and facade/CLI tests | PASS |
| Custom controller routing and actor provenance | Real SQLite plus Null/T-min/REF/BAD spies | PASS |
| All fixture schemas, integer cents, vocabulary, refs, loader balances/quarantine | 48 fixture tests; 11 real-loaded bundles | PASS |
| Factory selection, custom-controller harness isolation, provider-error propagation | Eight counted owner-local factory tests | PASS unit lane; actual provider absent |
| Regression comparisons, quotes, permitted explanatory extras and failure paths | 61 app tests using actual contract records and pure citation resolver | PASS unit lane |
| All specified CLI commands, errors, doctor and persistence workflows | 39 CliRunner tests | PASS |
| Actual Sonny financial validator, rules, harness, scheduler and factory | recoup.engine is absent | BLOCKED G2/G3 integration |
| Full H correction/credit/follow-up/notice/claim demo and regression 8/8 | Requires actual Sonny 007-4/5 and validator | BLOCKED G3 |
| Selected-case investigation isolation | Existing Controller.react signature has no case selector; CONTRACT_REQUEST.md unchanged | BLOCKED contract clarification |
| Contract F0 freeze, formal integration review/verification and merges | No freeze/tag/merge authorized here | PENDING |

Final verification before the documentation-only checkpoint:

- `make check`: **439 passed**, no skips or warnings; ruff lint and formatting
  clean (45 Python files).
- `.venv/bin/python -m pytest tests/app -q`: **113 passed**.
- `.venv/bin/python -m pytest tests/cli -q`: **39 passed**.
- `git diff --check`: PASS.
- Diff against candidate for `recoup/contracts`, `pyproject.toml`, `Makefile`,
  and `AGENTS.md`: empty. DAG and integer-money checks pass in make check.
- Installed CLI subprocess smoke in a temporary DB: doctor, init, load H+C,
  status H, advance --to-next-due (day 3), history H all exit 0;
  check-regression exits 1 as required.
- Actual fixture regression with the explicitly labeled contract-stub runtime:
  r01–r07 FAIL, r08 quarantine PASS. This demonstrates honest failure reporting,
  not an engine acceptance pass. The working database is unaffected by the
  regression command's isolated in-memory worlds.

Business semantics remain in design/02; comparison rules cite §8.6. The r10
workflow permits owner-local unit doubles, never replacement shared types or
fake integration passes. Review found and tests now cover cross-case identity
reuse, ambiguous evidence-ID components, future evidence exposed by clock-only
advance, missing policy_ref loading, and gross inferred-U1 amounts after credits.
No PDF/OCR/vision or financial assertion-validator integration claim is made.

Every changed file relative to the starting checkout is listed below. Each is
within the Charles handoff ownership; unchanged user inputs are excluded.

- `.gitignore`
- `README.md`
- `cases/demo/C/bundle.json`
- `cases/demo/H/bundle.json`
- `cases/demo/N/bundle.json`
- `cases/policies/P-A.json`
- `cases/policies/P-B.json`
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
- `progress/charles/006-2B-WORLD-ACCEPTANCE.md`
- `progress/charles/006-3-WORLD-ACCEPTANCE.md`
- `progress/charles/006-4-ACCEPTANCE.md`
- `progress/charles/006-5-CLI-ACCEPTANCE.md`
- `progress/charles/006-SESSION-ACCEPTANCE.md`
- `progress/charles/PROGRESS.md`
- `recoup/app.py`
- `recoup/cli.py`
- `recoup/world/__init__.py`
- `recoup/world/clock.py`
- `recoup/world/hashing.py`
- `recoup/world/ids.py`
- `recoup/world/ledger.py`
- `recoup/world/lines.py`
- `recoup/world/store.py`
- `tests/app/test_build_integration.py`
- `tests/app/test_facade_unit.py`
- `tests/app/test_factory_unit.py`
- `tests/app/test_mutations_integration.py`
- `tests/app/test_regression_unit.py`
- `tests/cli/conftest.py`
- `tests/cli/test_routing.py`
- `tests/cli/test_sqlite_workflows.py`
- `tests/world/conftest.py`
- `tests/world/test_actions.py`
- `tests/world/test_core.py`
- `tests/world/test_fixtures.py`
- `tests/world/test_identity.py`
