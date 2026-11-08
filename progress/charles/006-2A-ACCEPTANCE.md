# 006-2A session record — 2026-11-08 PT

Unit lane implemented; real G1 integration is BLOCKED, not passed. F0 review and
Verifier approval remain outstanding. Scope: external r10 handoffs/006-charles.md,
“006-2A: Injectable app facade”; workflow/test exception: r10 design/04 §1–5.
Business and public facade references: design/02 §2, §4.4–4.5.

## Prerequisites and preservation

- The requested `~/recoup-006-charles-bundle-r10.md` was absent. Read the existing
  `/Users/charlieherbst/recoup/recoup-006-charles-bundle-r10.md` instead. It and the
  pre-existing untracked `arhcive/` directory were left untouched.
- Initial checkout: `main`, clean tracked files; no conflicts. Initial local
  branches: `main`, `006-1-contracts`. Both pointed to candidate
  `89675c0b6ac676fa28c3475f58134689b74c274c`. No existing 006-2 work or tip was found
  in branches, files, history, or `progress/charles/PROGRESS.md`.
- `git fetch origin`: exit 0, no updates. Candidate ancestry check
  `git merge-base --is-ancestor 89675c0b6ac676fa28c3475f58134689b74c274c HEAD`:
  exit 0. Required owned predecessors: none (r10 design/04 §5).
- `git diff --exit-code 89675c0b6ac676fa28c3475f58134689b74c274c HEAD -- recoup/contracts`:
  exit 0; working-tree contract diff also empty. No contract change or rebuild.
- Created `006-2a-injectable-app-facade` from the existing candidate checkout.
  Local implementation tip is recorded in PROGRESS.md; no push/merge/tag.

## Public surface and unit evidence

The constructor is `Recoup(config, world, controller, parts, llm,
next_due_day=optional_callable)`. Inputs use the actual candidate contract types;
owner-local spies stay in `tests/app`. There is no production World in this step.

| Acceptance | Unit evidence in tests/app |
| --- | --- |
| Config/defaults/environment validation, no import-time providers | `test_config_unit.py`: `test_defaults_are_offline_and_no_environment_is_cached`, `test_vision_environment_boolean`, `test_invalid_environment_fails_explicitly`, `test_import_does_not_load_world_engine_or_llm_provider` |
| Lazy World construction, missing provider is explicit | `test_config_unit.py::test_build_propagates_missing_provider_without_fallback` (injected import error, not integration) |
| All nine public mutation routes, positional/keyword arguments, one callback, no engine investigate/handle calls or default assembly | `test_facade_unit.py::test_public_mutations_dispatch_only_to_selected_controller`, parameterized over NullController spy, scripted T-min spy, REF, BAD; each covers advance with and without events; provider imports and default parts/controller/LLM construction raise if attempted |
| Clock-only callbacks occur between daily advances | `test_clock_callbacks_interleave_each_day_even_without_events` |
| World results/errors remain visible; failed World calls do not dispatch; controller failure propagates | `test_mutation_return_records_are_not_replaced_by_controller_output`, `test_world_gate_errors_propagate_without_controller_dispatch`, `test_controller_failure_propagates_preserving_world_event`, `test_duplicate_evidence_still_dispatches_once` |
| Directory intake and batch callback, validation before writes | `test_load_batch_validates_all_inputs_then_dispatches_once`, `test_invalid_later_bundle_does_not_partially_load`, `test_load_requires_bundle_directories_and_handles_empty_list` |
| Run callback and returned view selection | `test_run_returns_views_after_callback_and_checks_unknown_case` |
| Clock arguments and injected due lookup | `test_invalid_clock_arguments_do_not_mutate`, `test_zero_days_and_conflicting_clock_arguments`, `test_next_due_injection_and_no_due_work`, `test_due_today_runs_callback_without_advancing_clock` |
| Read/tool routes use supplied EngineParts, no reaction | `test_read_exports_and_tool_sessions_use_injected_parts_without_reacting` |
| Constructor retains supplied ports and isolates config/run id | `test_constructor_preserves_config_and_uses_supplied_ports` |
| Deferred functionality fails explicitly | `test_unwired_due_lookup_and_regression_gate_are_explicit` |

The per-case `run` test proves callback routing and returned views only. It does
not prove engine investigation scope: the current Controller.react signature
receives World, events and run_id, with no explicit selected-case argument.
See CONTRACT_REQUEST.md. No change to that contract was made in this facade-only
session.

## Commands and results

- Baseline `make check`: ruff lint/format PASS; **201 passed**.
- Final `RECOUP_LLM=fake .venv/bin/python -m pytest tests/app/test_config_unit.py tests/app/test_facade_unit.py -q`:
  **36 passed**.
- `RECOUP_LLM=fake .venv/bin/python -m pytest tests/app/test_build_integration.py -ra`:
  **1 skipped**, explicitly `BLOCKED G1: real SqliteWorld provider requires 006-2B`.
- Final `make check`: ruff lint/format PASS; **237 passed, 1 skipped**.
  That skip is the blocked G1 test, not an integration pass.
- `git diff --check`: PASS. No unrelated baseline test failures; an initial lint
  attempt found one import-order issue and one long line, both corrected.

## Real integration status

| Required check | Status | Missing provider |
| --- | --- | --- |
| `test_build_real_sqlite_world_with_contract_stubs` | BLOCKED (explicit skip) | 006-2B `recoup.world.store.SqliteWorld` |
| Original 006-2 G1 World acceptance: quarantine, evidence supersession/redelivery, proposal no-op, immutable facts/hash/history, transaction rollback, full fact confirmation/historical citation flow | BLOCKED; not implemented/executed here | 006-2B real SqliteWorld and tests/world |
| Default due-work/held-event lookup and `advance(to_next_due=True)` against persisted state | BLOCKED | 006-2B real World lookup/adapter |
| Factory/harness/LLM isolation with actual engine assembly | BLOCKED | 006-5 wiring and Sonny 007-4/5 providers (G3) |
| `run(A)` investigates A only in a two-case real-controller test | BLOCKED | Selected-case contract clarification (CONTRACT_REQUEST.md) and actual controller |

`build` currently uses existing shared contract stubs, a NullController default,
and no harness. Its lazy real World import cannot succeed at this checkout.
`next_due_day` works with an injected lookup; without one it explicitly awaits
006-2B. `check_regression` explicitly awaits 006-4 fixtures/006-5 wiring. These are
not substitute integration implementations. No finance safety claim follows
from World spies, PassValidator, or MOCK fixture receipts.

## Changed files

- `recoup/app.py`
- `tests/app/__init__.py`
- `tests/app/conftest.py`
- `tests/app/doubles.py`
- `tests/app/test_config_unit.py`
- `tests/app/test_facade_unit.py`
- `tests/app/test_build_integration.py`
- `progress/charles/006-2A-ACCEPTANCE.md`
- `progress/charles/CONTRACT_REQUEST.md`
- `progress/charles/PROGRESS.md`

All are within the session's owned paths. No dependencies, shared contracts,
World implementation, 006-1 files, external actions, paid calls, sends or next
implementation step were added. Stop after this session.
