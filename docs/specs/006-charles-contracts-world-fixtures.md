# 006: Contracts, World, composition root, CLI, fixtures (owner: Charles)
**Status:** design review pending. The contract is PROPOSED v1. It freezes at F0, after the Reviewer and Verifier pass PR 006-1.
**Supersedes:** specs/001 (kept as history).
**Design refs:** design/01; design/02 §2–§4, §7, §8.1, §9.

## Owns (exclusive)
- `pyproject.toml`, `Makefile`, `.gitignore`, `README.md`, root `AGENTS.md`, `docs/**`
- `recoup/__init__.py`, `recoup/contracts/**`, `recoup/world/**`, `recoup/app.py`, `recoup/cli.py`
- `cases/**`, `bench/holdout/**` (commits the Bench bot drop unedited)
- `tests/contracts/**`, `tests/world/**`, `tests/app/**`, `tests/cli/**`, `progress/charles/**`

**Never touch:** `recoup/engine/**`, `recoup/ui/**`, `recoup/bench/**`, `bench/dev|episodes|results/**`, `bench/PLAN.lock`, `bench/prices.json`, or other people's tests or progress.

## Steps and gates
1. **006-1 → G0/F0: contracts + docs.**
   - Create `pyproject.toml`:
     - deps: `pydantic>=2,<3`, `typer`, `streamlit`, `openai`, `pypdf`
     - extras: `ocr=[pytesseract, pillow]`, `dev=[pytest, ruff]`
     - script: `recoup=recoup.cli:app`
     - pin versions after install.
   - Add `make check`.
   - Add root `AGENTS.md`, `docs/design/01-03`, `docs/specs/006-008`, `docs/harness/*` and `docs/INDEX.md`.
   - Create the contract files `recoup/contracts/{money,models,bundle,tools,interfaces,oracle,resolve,testing}.py` exactly as in design/02 §3.1–3.5 and §8.1.
   - **Tests:**
     - round-trip every model;
     - `tool_json_schemas()` covers every registry entry;
     - `parse_usd`/`bp_of` half-even cases;
     - import-DAG AST test exactly as design/02 §2;
     - stubs smoke test.
   - After the review passes: tag `contract-v1` and add a LOG line.
2. **006-2 → G1: SqliteWorld core + `app.build` with stub EngineParts (design/02 §2 G1, §4.5).**
   - `recoup/world/{store,ledger,clock,ids,hashing,lines}.py`.
   - Constructor: `SqliteWorld(path, ingestor, validator)`.
   - Implement:
     - `load_bundle` (non-USD → quarantine)
     - ledger intake
     - deduction lines (§3.7, including U1/NP)
     - active evidence and supersession/duplicate rules (§3.6)
     - evidence hash
     - `save_decision` versioning
     - `save_proposal`/`edit_proposal` identity (§3.8)
     - approve/reject
     - `view`/`history`/`list_cases`/`list_quarantined`
     - `allowed_recipients`
     - append-only `add_fact`/`confirm_field`/`set_line_reason`, `fact_set` (current and historical, incl. `docs`), `resolve_citation` incl. `fact:` locators (delegating to pure `contracts/resolve.py`, 006-1), `advance_to(..., release_events=False)`, `transaction()` (§3.2, §3.5–3.7)
     - `app.build(RecoupConfig(db=":memory:"))` with stubs; controller injection (§4.5)
   - **Tests:**
     - quarantine of an EUR bundle (no Money);
     - v1-after-v2 is inactive;
     - identical redelivery is a no-op;
     - conflicting redelivery → needs_human;
     - identical proposal save is a no-op;
     - an identical fact revision is a no-op; a changed one changes `evidence_set_hash`; Evidence rows never change;
     - an exception inside `transaction()` rolls back every write;
     - pure resolver: `contracts.resolve.resolve_citation` with an old FactSet, evidence and fact rows (no World) returns the old value after a later revision;
     - fact flow: a required fact absent from source fields is extracted from text (`add_fact`, model_extracted), then confirmed (new revision), and appears in `fact_set`; after a further revision, `fact_set(old_basis_hash)` and `resolve_citation(fact:<old id>, old_basis)` still return the old value, and the Evidence row is byte-identical throughout.
3. **006-3 → G2: submit, staleness, events, due work.**
   - `submit` in the exact §4.3 step order, writing an `ActionAttempt` for every call.
   - Mocks with receipt prefixes, and `fail_next`.
   - The cascade (§4.2), including reopening closed cases and the balance-basis rule.
   - `advance_to`, held docs and `attach_held`.
   - Domain events; DueWork.
   - **Tests:**
     - no approval → GateError;
     - stale after evidence → GateError;
     - resubmit after a later cascade still returns the same receipt (replay check first);
     - two approved credits on one line, where the second exceeds the remaining valid amount → GateError;
     - a new proposal id under a submitted business key is rejected;
     - posting a credit makes the notice stale;
     - receipts survive the cascade;
     - a changed fact revision voids the approval;
     - the §4.5 spy test across every public Recoup mutation (0 harness calls for Null/T-min stub/REF/BAD; one react per mutation);
     - after reopening the DB, pending events and due work are returned exactly once.
4. **006-4: fixtures** (may start after G0). All values come from design/01 §10 and the §3.7 vocabulary.
   - `cases/policies/P-A.json` and `P-B.json`.
   - `cases/demo/{H,C,N}`. H includes the day-3 POD v2 + inspection event and has no statement doc.
   - `cases/regression/r01..r08`, each with `bundle.json` and `oracle.json` (CaseOracle with evidence refs). Coverage:
     - ≥ 7 of the 9 reasons;
     - an unsigned POD → needs_info;
     - damage reported outside the window under a contract with `damage_late_waived` absent → needs_info/unsupported_terms;
     - an unauthorized amendment;
     - P-B nonpayment with the balance over the credit limit (its oracle sets `claim_items` by §5.6 ids, e.g. `claim.credit_limit: restricted`);
     - an EUR bundle → quarantined.
   - Fixture validator test: bundles parse, keys are in the vocabulary, and the cents reconcile.
5. **006-5 (after 007-4 + 007-5 merge; merging it completes G3): wire `recoup.engine.factory` + CLI.**
   - `recoup/app.py` (§4.5), including `check_regression`.
   - `recoup/cli.py` (§7), including `doctor` and `check-regression`.
   - **Tests** (via CliRunner):
     - `load` with 2 paths;
     - `advance --to-next-due` processes events automatically;
     - `check-regression` exits nonzero on a mismatch.

## Acceptance (the Verifier checks these)
- `make check` is green offline.
- The contract files match design/02 §3 and §8.1.
- Every listed test exists and passes.
- No float is used for money in contracts or world (grep test).
- The DAG test passes.
- No network access.

