# Charles World handoff to Sonny — 2026-11-09

The Charles persistence prerequisites are implemented in the existing `SqliteWorld`. Normative behavior lives in design/02 §3.4, §3.7–3.9 and §5.4–5.5; use those sections for engine behavior rather than this implementation note.

Use the imported `recoup.contracts.remittance` models with `world.load_remittance(bundle, bundle_dir=None)` and `world.remittance_history(remittance_id=None)`. App/CLI integration belongs to Charles. The historical payment path creates neither external-action approvals nor mock action receipts. Its source and outcome records remain in the same SQLite database and transaction system as case intake.

For counteroffers, the World now supplies `FactSet.buyer_senders`, persists `offer_ref` on approvals/receipts and checks financial boundaries independently of the injected validator. Sonny must still implement the engine rules, proposal derivation, semantic validator, tool argument flow and FakeLLM/event behavior specified by §5.4–5.5 and task 007-8. No new World or copied contract models are necessary. Required offer fact citations must actually appear in the proposal's citations. The first version requires complete, consistent buyer emails as specified in §5.4. Human edits retain the original line set, including any zero-valued allocations.

`add_fact` now rejects absent, non-resolving or value-mismatched backing citations before writing a revision. `fact_set` resolves every emitted citation before exposing facts. The caller must pass a genuine supporting citation, including when confirming a source field; evidence source rows stay immutable.

Existing databases with supported cited facts remain readable. Old persisted historical FactSets created before `buyer_senders` existed deserialize with its empty default; negotiation rules must fail closed on those old snapshots. New current and persisted FactSets contain the allowlist. Legacy uncited or unsupported fact revisions fail closed when exposed and require an explicit data migration; ordinary `add_fact` cannot repair an already invalid current basis. No automatic migration was performed. Source evidence stays immutable.

Changed files in this World subtask:

- `recoup/world/store.py`
- `recoup/world/remittance.py`
- `tests/world/test_remittance.py`
- `tests/world/test_counteroffer_boundary.py`
- `progress/charles/SONNY-WORLD-HANDOFF.md`

Validation: the complete World test directory passes (145 tests, including the existing 97). Tests cover cash conservation, immutable source identity and history, replay/restart, currency quarantine before Money, invalid references without partial intake, prior bank cash, simulated dates, transaction rollback, conflicting evidence, source trust, cited offer identity, receipt reservations, human edits and approval binding. The parent Charles session runs the repository-wide `make check` before final delivery.
