# Sonny session handoff — 2026-11-09 (America/Los_Angeles)

Branch: `codex/007-4-harness-factory-ingestion`.
This handoff consolidates the completed, previously uncommitted 007-8 work and
its user-requested acceptance follow-ups. Detailed evidence and earlier session
records remain in [PROGRESS.md](PROGRESS.md). Historical instructions there to
leave this work uncommitted are superseded by the user's request to push it.

## Current implementation

- Counteroffer derivation, gates, selector flow, completion and FakeLLM coverage
  are implemented and covered by actual app-built SQLite acceptance tests.
- Offer-reference compatibility, approval/receipt binding, repeated-source sender
  consistency and selected-case isolation have explicit acceptance coverage.
- Approved legal, buyer-classification and citation consumers are verified;
  scheduler ordering and both buyer sender allowlists have integration coverage.
- Engine scan/factory capability reporting uses the shared contract probe.
- Shared remittance intake is consumed through the existing engine handler path.

Normative sources: design/02 §3.7–3.9, §4.5 and §5.3–5.8. Shared publication:
`933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f`; implementation:
`75a58397bec3846847673ef8af4c7ae85d2a5264`; contracts tree:
`fb064458d4070d7290bd0f242a28d56f1c31aac7`. No shared contracts, dependencies
or Charles-owned handoffs were edited in this publication step.

## Verification

- `make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint/format PASS;
  **1038 passed, 2 skipped in 116.15s**. The two optional OCR tests are skipped.
- `RECOUP_LLM=fake /tmp/recoup-007-check/bin/python -m recoup.cli --db :memory: check-regression`:
  **8/8 PASS**, actual engine runtime, SYNTHETIC data, MOCK actions, LLM fake.
- Prior full H/C/N demo acceptance is recorded in PROGRESS.md; not rerun in this
  publication-only step. Live-model and real OCR acceptance remain unclaimed.

## Files in this publication

- `progress/sonny/CONTRACT_REQUEST.md`
- `progress/sonny/PROGRESS.md`
- `progress/sonny/SESSION-HANDOFF.md`
- `recoup/engine/counteroffers.py`
- `recoup/engine/derive.py`
- `recoup/engine/factory.py`
- `recoup/engine/gates.py`
- `recoup/engine/harness.py`
- `recoup/engine/rules.py`
- `recoup/engine/scans.py`
- `recoup/engine/scheduler.py`
- `recoup/engine/tools.py`
- `tests/engine/test_007_5_integration.py`
- `tests/engine/test_007_8_integration.py`
- `tests/engine/test_counteroffer_harness.py`
- `tests/engine/test_offer_ref_acceptance.py`
- `tests/engine/test_rules.py`
- `tests/engine/test_scan_ingest.py`

All files are within Sonny's handoff ownership. Next: reviewer/verifier review of
this published branch. Stop here; no next implementation step is authorized by
this handoff update. No outstanding question for the offline acceptance lane.
