# Charles World integration boundary acceptance — 2026-11-08 PT

Scope: Charles-owned SQLite integration seams exposed by the published Sonny
engine branch. Contract semantics remain in design/02 §§3.5, 3.7, 4.2 and 5.7.
The shared contracts, engine sources, dependencies and Git history were not changed.

`set_status` normalizes incoming engine values with the existing contract enums
before its single SQL update. An invalid value, including an empty string, raises
before status, insurance or reason can change. Fact revision events now reference
their owning evidence; the explicit cascade trace still records the fact ID.
Line-reason revision events use the supplied citation, the line's evidence source,
or actual invoice/payment evidence tied to an existing ledger source.

For an older/incomplete database whose inferred line has no remaining backing
evidence, a line-reason change retains its immutable revision and cascade trace
without creating an event that falsely claims an evidence ID exists. Such a
database needs explicit re-investigation; no new contract event was invented.

Verification:

- The new boundary tests ran against the original implementation first:
  **10 failed, 1 passed**, reproducing status `AttributeError`, invalid evidence
  refs and the fabricated line event.
- After the fix: **11 passed** in `tests/world/test_engine_boundary.py`.
- Entire World suite: **97 passed**.
- `make check` in the shared checkout: **450 passed, 3 skipped**; all lint and
  format checks pass. The skipped real-engine acceptance tests belong to the
  parallel app task because the published Sonny branch is not merged here.
- `git diff --check`: pass.
- SQLite tests use only the existing fixture's explicit ingestor/validator stubs
  and the existing network prohibition. Actual published-engine acceptance is
  run separately in the parent's temporary combined snapshot.

Files changed for this task:

- `recoup/world/store.py`
- `tests/world/test_engine_boundary.py`
- `progress/charles/006-INTEGRATION-WORLD-ACCEPTANCE.md`

The parent session owns the required three-line `progress/charles/PROGRESS.md`
update so parallel tasks do not race on that file.
