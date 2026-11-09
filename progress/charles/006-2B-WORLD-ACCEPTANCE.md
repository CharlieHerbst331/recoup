# 006-2B World core acceptance

References: design/02 §2, §3.5–3.8, §4.1, §4.5; spec 006 step 006-2. The external r10 handoff permits unit doubles; the World tests below exercise actual SQLite, with the contract TextOnlyIngestor and PassValidator as explicit ingestion/validation stubs. They do not establish Sonny finance-gate correctness.

| Acceptance | Evidence | Result |
|---|---|---|
| EUR quarantine creates no case/evidence/ledger/Money | `test_quarantine_has_no_case_evidence_ledger_or_money` | PASS |
| Ledger intake; U1, NP, pre-existing credit; allowed recipients | `test_ledger_lines_and_allowed_recipients`, `test_nonpayment_and_zero_payment_deductions_never_make_np` | PASS |
| Lower version inactive, duplicate no-op, conflict escalates; evidence byte immutability | `test_supersession_reverse_order_duplicate_and_conflict` | PASS |
| Fact extract → confirm → later revision; immutable Evidence; current and old FactSet/docs | `test_fact_flow_immutable_rows_and_historical_basis`, `test_source_confirmation_bool_quote_and_fact_noop` | PASS |
| Pure historical citation resolver without World | `test_fact_flow_immutable_rows_and_historical_basis` directly invokes contract resolver on stored basis/evidence/fact rows | PASS |
| Effective facts drive deduction intake; line reasons append and alter hash | `test_deduction_intake_uses_effective_facts_without_mutating_evidence`, `test_line_reason_revisions_are_append_only_and_hash_changes` | PASS |
| Entire transaction and nested savepoint rollback; no residual clock/tables | `test_transaction_rolls_back_every_table_and_clock`, `test_nested_transaction_rollback_keeps_outer_work` | PASS |
| Decision versions/current; stale basis rejected | `test_decision_versioning_and_stale_basis_rejection` | PASS |
| Proposal identity/no-op; new versions; scoped approval, rejection, immutable approved edits | `test_proposal_identity_versioning_edits_approval_and_reject`, `test_edit_recipient_and_allocation_limits`, `test_validator_is_called_at_save_and_approve_and_rolls_back` | PASS |
| Real file restart preserves clock/bases/due work; due idempotency | `test_persistence_clock_basis_and_due` | PASS |
| Integer-only contracts and World code | `test_no_money_float_literals_or_annotations` | PASS |
| Actual `app.build` integration | `tests/app/test_build_integration.py`, root-owned | PASS in full suite |
| Actual Sonny ingestion/validator/engine integration | Providers absent; explicit stubs only | BLOCKED, subsequent gates |

Commands: `python -m pytest tests/world -q` through `.venv/bin/python`: **64 passed** (16 core plus 48 fixture tests). `make check`: ruff clean, formatting clean (36 files), **304 passed** in 1.08s. No network used.

Owned changes in this delegation: `recoup/world/__init__.py`, `recoup/world/clock.py`, `recoup/world/hashing.py`, `recoup/world/ids.py`, `recoup/world/ledger.py`, `recoup/world/lines.py`, `recoup/world/store.py`, `tests/world/conftest.py`, `tests/world/test_core.py`, this acceptance file. Root and fixture-agent changes are recorded separately.

Deferred exactly to 006-3: submit/mock failure semantics, evidence/fact/ledger staleness cascade, timed evidence and held-document release. Core method seams exist and fail explicitly until enabled. Root app/progress/checkpoint work remains with the parent agent.
