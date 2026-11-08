# 006-1 verification — 2026-11-08 PT

Status: implemented locally, **PROPOSED v1**; Reviewer/Verifier review and F0 remain pending.
Normative references: `docs/design/02-technical-design.md` §2, §3, §8.1.

## Acceptance to evidence

Test paths below are relative to `tests/contracts/`.

| 006-1 item | Proving test / evidence |
|---|---|
| Python 3.11, installed packaging, required dependencies, pinned versions, dev/OCR extras, configured future CLI entrypoint | `test_bootstrap.py::test_packaging_pins_extras_and_future_entrypoint`; editable `.[dev]` installation succeeded using `.venv/bin/python` (3.11.12); `pip check` reported no broken requirements. The CLI was never invoked. |
| Bundle documentation, root instructions, document index | `test_bootstrap.py::test_bootstrap_docs_and_index`; independent byte comparison against every bundle FILE section passed for all ten docs and root AGENTS.md. No prior documentation differed. |
| All named contract files, models, fields, defaults and port signatures match the design | `test_design_contract.py::test_normative_model_fields_and_port_signatures`; model and registry tests below. Runtime protocol checks permit the specified EngineParts container to accept structural implementations. |
| Round-trip every model, including oracle/run-record models | `test_models.py::test_every_model_round_trip`: 85 wire models round-trip through JSON; EngineParts round-trips its four injected Python port objects through model_dump/model_validate. `test_scalar_json_types_survive` checks every Scalar alternative; `test_mutable_defaults_are_independent` checks independent mutable defaults. |
| Tool-schema registry coverage and benchmark-tool separation | `test_tools.py::test_tool_schema_registry_coverage` (both include_bench modes); `test_registry_names_and_bench_separation`; `test_policy_exclusion_citations_survive_round_trip`. All 16 product and two bench tools are covered. |
| USD money with half-even rounding | `test_money.py::test_parse_usd_half_even`, `test_bp_of_half_even`, `test_parse_usd_invalid`, `test_integer_money_currency_and_freezing`, `test_fmt_and_clamp`. Includes positive/negative ties and large integer precision. |
| No float money in contracts or World | `test_money.py::test_no_float_money_in_contracts_or_world` scans all existing files in both areas for float literals/types/calls. World is intentionally absent in 006-1. |
| Import DAG for production and test paths, at every AST depth | `test_import_dag.py::test_repository_import_dag`, `test_guard_rejects_forbidden_edges`, `test_guard_allows_normative_edges`. Includes function bodies, TYPE_CHECKING, relative imports, literal dynamic imports/aliases, non-literal dynamic imports and app factory placement. |
| Pure citation resolver, including historical provenance | `test_resolve.py::test_source_locator_resolution`, `test_invalid_citation_rejected`, `test_historical_fact_resolves_after_revision_without_world`, `test_historical_evidence_uses_basis_membership`, `test_fact_provenance_is_validated`, `test_missing_and_cross_case_evidence_rejected`. |
| Contract stubs smoke tests | `test_stubs.py::test_stub_parts_engine_smoke`, `test_validator_and_null_controller_smoke`, `test_text_only_ingestor_smoke`, `test_text_only_ingestor_text_file`, `test_stub_tool_session_smoke_and_traces`, `test_stub_read_fact_locator`, `test_scripted_llm_smoke`, `test_gate_error_exposes_issues`. World is an autospecced port mock, not another implementation. |
| make check green offline, without an API key or model call | All tests use `conftest.py::offline_without_api_keys` (autouse): API-key environment variables removed, fake mode selected, socket connections and DNS blocked. Stub engine smoke test asserts zero LLM calls. `make check` runs only local ruff and pytest. |
| Remain inside 006-1 ownership; preserve existing work | Final staged-path audit passed. The original untracked bundle remains unchanged and uncommitted. No World, engine, app, UI, benchmark, fixture or CLI implementation was created. |

## Results

```text
.venv/bin/python -m ruff check recoup tests
All checks passed!
.venv/bin/python -m ruff format --check recoup tests
19 files already formatted
RECOUP_LLM=fake .venv/bin/python -m pytest
201 passed in 0.41s
```

The approved bundle was found at `./recoup-006-charles-bundle.md`; the requested
home-directory location was absent. Its SHA-256 is
`f12e7dda1f4da1acd766d41f7ea4e5123e6d1b32dddeb83b986da9001464df97`.

No implementation blockers or contract requests. Review/F0 is pending; no tag,
push, merge, model API call or paid operation was performed. Step 006-2 was not started.

`git diff --cached --check` flags only the extra blank line at EOF inherited from
each verbatim bundle section (including root AGENTS.md). Those bytes are retained
to honor the requested extraction; there are no source-code whitespace findings.

## Changed files

- `.gitignore`
- `AGENTS.md`
- `Makefile`
- `README.md`
- `docs/INDEX.md`
- `docs/design/01-functional-design.md`
- `docs/design/02-technical-design.md`
- `docs/design/03-review-resolution.md`
- `docs/harness/AGENTS-engine.md`
- `docs/harness/AGENTS-root.md`
- `docs/harness/AGENTS-ui-bench.md`
- `docs/harness/SESSION-TEMPLATE.md`
- `docs/specs/006-charles-contracts-world-fixtures.md`
- `docs/specs/007-sonny-engine.md`
- `docs/specs/008-carter-workbench-bench.md`
- `progress/charles/006-1-ACCEPTANCE.md`
- `progress/charles/PROGRESS.md`
- `pyproject.toml`
- `recoup/__init__.py`
- `recoup/contracts/__init__.py`
- `recoup/contracts/bundle.py`
- `recoup/contracts/interfaces.py`
- `recoup/contracts/models.py`
- `recoup/contracts/money.py`
- `recoup/contracts/oracle.py`
- `recoup/contracts/resolve.py`
- `recoup/contracts/testing.py`
- `recoup/contracts/tools.py`
- `tests/contracts/conftest.py`
- `tests/contracts/test_bootstrap.py`
- `tests/contracts/test_design_contract.py`
- `tests/contracts/test_import_dag.py`
- `tests/contracts/test_models.py`
- `tests/contracts/test_money.py`
- `tests/contracts/test_resolve.py`
- `tests/contracts/test_stubs.py`
- `tests/contracts/test_tools.py`
