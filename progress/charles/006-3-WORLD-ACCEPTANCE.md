# 006-3 World transactions and actions acceptance

Business references: design/02 §3.8, §4.2–4.4. Real SQLite runs under the explicit contract TextOnlyIngestor/PassValidator test lane; these results prove World orchestration and defensive ledger limits, not the absent Sonny validator's complete financial/semantic gates.

| Required behavior | Test evidence | Result |
|---|---|---|
| No approval rejected; exactly one durable attempt for every call, including unknown id/version | `test_no_approval_and_unknown_calls_have_exactly_one_attempt` | PASS |
| Replay precedes stale state, validator, fail-next; credit posts once | `test_credit_posts_once_and_replay_precedes_stale_validator_and_failure` | PASS |
| Changed fact voids approval and stales proposal; identical fact revision is no-op | `test_stale_fact_voids_approval_and_identical_fact_does_nothing` | PASS |
| Scoped approval exact match, current decision, validator stage submit | `test_approval_binding_tamper_and_validator_submit_stage`, `test_new_decision_invalidates_old_decision_binding_at_submit` | PASS |
| Aggregate duplicate allocations; remaining valid amount; pre-existing credits; open balance; business identity | `test_aggregate_duplicate_credit_allocations_cannot_bypass_valid_guard`, `test_remaining_credit_and_business_key_guards`, `test_preexisting_credit_and_open_balance_guards` | PASS |
| Receipt-specific correction pools, supplements, prior corrections and duplicate allocations | `test_corrections_use_per_receipt_per_line_pools`, `test_correction_cannot_withdraw_credit_or_other_case_receipt` | PASS |
| Posted credit stales notice/claim/readiness, voids approval, cancels dependent due work | `test_notice_and_claim_stale_on_balance_and_due_cancelled` | PASS |
| Closed case reopens; one cascade trace; receipts/ledger byte preservation | `test_cascade_reopens_closed_and_keeps_receipts_and_ledger_bytes` | PASS |
| Fail-next durable across restart; transient rollback; successful retry and replay restart | `test_transient_rollback_retry_and_restart` | PASS |
| Unexpected failure after receipt/ledger writes rolls back every effect, retaining one audit attempt | `test_exception_after_receipt_rolls_back_all_effects_and_is_audited` | PASS |
| Pending events/due survive restart, explicit processing persists, held docs only fetchable after availability, fetch transient retry | `test_events_due_and_held_visibility_survive_restart_exactly_once` | PASS |
| Direct future evidence stays hidden during calendar-only advance and enters ledger only on release | `test_future_direct_evidence_is_hidden_during_calendar_only_advance` | PASS |
| Gross classified U1 claim persists after mock credits | `test_classified_unexplained_claim_stays_gross_after_posted_credit` | PASS |
| Evidence component collisions and cross-case readiness/decision/proposal ownership | `tests/world/test_identity.py` first two tests | PASS |
| Reference-only policy load, embedded dedupe, missing/unsafe policy rollback | `tests/world/test_identity.py` policy tests | PASS |
| Real app mutation isolation and day-3 release | `tests/app/test_mutations_integration.py`, root-owned | PASS |
| Actual Sonny validator/ingestor/scheduler integration | Those providers are absent; stubs remain explicitly labeled | BLOCKED, no G3 finance claim |

Verification: `.venv/bin/python -m pytest tests/world tests/app -q`: **130 passed**, no warnings. `make check`: ruff clean, formatting clean (39 files), **331 passed** in 0.88s, no warnings. All tests offline.

Representation notes, without changing contract models:

- Evidence identity retains the documented `EV-<case>-<ref>-v<version>` format, percent-escaping `%` and `-` inside components to preserve tuple identity. Ordinary H/POD IDs remain unchanged.
- U1 uses source pre-existing credit-document intake when calculating the inferred gross claim; later mock credits affect open balance without shrinking that claim. NP uses current open balance. See design/02 §3.7 and §5.3.
- Changed fact revisions emit the existing `evidence_added` event with the new fact id; changed line reasons use the source evidence ref (line id fallback). One cascade trace records the revision kind/id. This adapter choice awaits actual Sonny scheduler integration.
- Unknown submit attempts persist under `__unknown__`; missing versions of a known proposal use its real case. Actor provenance uses `world.attempt_controller`, set by the root's app assembly from the selected controller.

Changed owned files: `recoup/world/ids.py`, `recoup/world/lines.py`, `recoup/world/store.py`, `tests/world/test_actions.py`, `tests/world/test_identity.py`, this acceptance file. Shared progress and checkpoint belong to the root agent. No contract, engine, fixture or unrelated file changes in this delegation.
