# 006-5 CLI acceptance — 2026-11-08 PT

Scope: design/02 §7 and §4.5; external r10 design/04 §3–5. The parent session
verified candidate ancestry, the required 006-3 implementation tip
`5746ad58bd2d4935969f023e9a03bdfcba306050`, and unchanged candidate contracts
before enabling this task. No branch switch, commit, merge, dependency change,
or external action was performed by this subtask.

Implemented every §7 command through `recoup.app.build` and the facade:
`init`, `load`, `run`, `advance`, `add-evidence`, `confirm-field`, `edit`,
`approve`, `reject`, `submit`, `status`, `history`, `doctor`, and
`check-regression`. Global `--db` overrides `RECOUP_DB`; other existing config
environment variables retain their app behavior. All workbench output includes
SYNTHETIC/MOCK/LLM provenance and the runtime provider. Contract-stub mode names
the missing engine and finance-validator integration explicitly.

Typed CLI usage errors exit 2. File/JSON/config, gate, transient, unavailable
provider/import, and other expected human-facing errors exit 1 with their
reason. Unexpected programming errors remain visible; no fallback provider is
invented. Repeated `--line LINE=CENTS` values require distinct line ids and
nonnegative integer cents; draft files are UTF-8 and document-relative paths
resolve beside the supplied document JSON. SQLite resources close after each
command, including failures.

`doctor` checks local dependency/executable presence without building the
engine or opening a database. It prints only API-key presence, never values;
vision/provider functionality is explicitly unverified. No network calls are
made. `check-regression` lists every case result and mismatch, exits 1 if any
case fails, and rejects an empty result as a failure.

| Acceptance | Evidence | Result |
| --- | --- | --- |
| Every command routes to the documented facade/world read surface | `tests/cli/test_routing.py::test_all_command_routes`, `test_initialization_status_and_db_override`, `test_document_and_full_edit_arguments` | PASS; counted ports, not engine integration |
| Usage/domain/file/provider errors, resource closure, allocations | Routing tests `test_usage_errors_exit_two`, `test_domain_errors_are_readable_and_close_resources`, `test_file_and_json_errors_are_readable_before_assembly`, allocation tests | PASS |
| Regression mismatch exits nonzero; successes and empty runs handled | `test_regression_pass_and_failure_exit_codes` | PASS |
| Doctor runs without provider/DB/network or secret disclosure | `test_doctor_without_assembly_database_network_or_secret_output` | PASS |
| Load two independent paths; persistent status/history and EUR quarantine | `tests/cli/test_sqlite_workflows.py::test_load_two_paths_status_history_quarantine_and_init` | PASS; actual app-built SQLite |
| `advance --to-next-due` releases evidence and dispatches each day automatically | `test_advance_next_due_releases_events_and_dispatches_automatically` | PASS; actual SQLite and an explicitly counted processing controller |
| Actual confirmation, relative-file ingestion, reduced edit/versioning, approval, rejection, mock credit, replay and attempt audit | `test_confirm_add_relative_text_edit_approve_submit_replay_and_reject` | PASS; actual SQLite and contract validator; not Sonny finance-gate proof |
| Actual regression fixtures fail honestly under incomplete engine stubs | `test_real_regression_gate_reports_stub_mismatches_and_quarantine` | PASS: seven regression mismatches reported, EUR quarantine passes, exit 1 |
| Actual engine/factory/handler demo and CLI smoke (G3) | Missing Sonny `recoup.engine.factory` and 007-4/5 implementation | BLOCKED; no substitute integration pass |

Commands and results:

- `RECOUP_LLM=fake .venv/bin/python -m pytest tests/cli -q`: **39 passed**, no warnings.
- `make check`: ruff check PASS; formatting PASS; **439 passed**, no skips or warnings.
- `.venv/bin/recoup --db :memory: doctor`: exit 0. Actual local report:
  engine absent; text-layer PDF installed; OCR Python packages installed but
  `tesseract` executable absent, so OCR unavailable; vision not requested;
  no key configured; network not checked.
- `git diff --check`: PASS.

Files created by this subtask only:

- `recoup/cli.py`
- `tests/cli/conftest.py`
- `tests/cli/test_routing.py`
- `tests/cli/test_sqlite_workflows.py`
- `progress/charles/006-5-CLI-ACCEPTANCE.md`

Done: CLI and owned command/SQLite verification are complete within 006-5 scope.
Next: parent integrates app composition/regression changes and records final checks/tip.
Question: G3 requires Sonny providers and the existing selected-case controller clarification.
