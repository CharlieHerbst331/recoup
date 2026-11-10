# Integration merge to main — 2026-11-09

The user explicitly requested merging
`006-2b-sqlite-world-core-and-app-build` into `main` and closing superseded PR #1.

Merge inputs:

- Main: `fc425ce362bc71fad6afc584e854edfd21e9b3fe`.
- Tested integration: `73b7f194244c77767a97bfc5b8b66ad82f8bb3ca`.
- PR #1 head: `54076cb7160274db64f598698b359193bba41e40` on
  `007-0-rule-test-vectors`, targeting `main`.

Git ancestry confirms that PR #1's exact head commit is already included in the
integration source. The merge preserves both parents and all existing history;
it does not squash, rebase or force-update main. The rule vectors therefore do
not need a separate merge.

The only conflicts were README.md, docs/INDEX.md and
progress/charles/PROGRESS.md. Resolutions preserve main's earlier owner F0
acceptance and the integration branch's current implementation documentation
and complete progress history. The 006-1 acceptance file from main is preserved.
The merge also adds this acceptance record and the required progress entry.

No implementation, test, dependency, contract, fixture or engine file differs
from the tested integration source. The shared contract tree remains
`fb064458d4070d7290bd0f242a28d56f1c31aac7`. No contract tag was created.

Validation and delivery:

- Required merged-tree `make check`: lint/format PASS; **1047 passed, 2 optional
  OCR skips** in 216.76 seconds. Actual-engine CLI regression: **8/8 PASS**.
- No unresolved merge markers or unmerged index entries remain.
- Source-relative whitespace check passes. The full staged whitespace check
  retains the source branch's existing extra EOF blank line in engine/AGENTS.md;
  that file is unchanged by conflict resolution.
- Push uses the ordinary non-force `main` update, preserving remote changes.
- PR #1's state is checked after main publication and closed only if still open.
  Source and PR branches are retained.

The user-requested main merge supersedes earlier branch acceptance notes saying
main had not yet been merged. It does not assert independent Reviewer/Verifier
sign-off, live-model proof or real OCR acceptance. Known limits remain documented
in 006-FINAL-INTEGRATION-ACCEPTANCE.md. The original untracked `arhcive/` directory
and input bundle remain untouched and excluded.

## Files changed relative to previous main

The complete merge change list is recorded below before committing.

- `.gitignore`
- `README.md`
- `cases/ambition/README.md`
- `cases/ambition/counteroffer/bundle.json`
- `cases/ambition/multi-invoice/remittance.json`
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
- `docs/INDEX.md`
- `docs/design/01-functional-design.md`
- `docs/design/02-technical-design.md`
- `docs/specs/007-sonny-engine.md`
- `progress/charles/006-2A-ACCEPTANCE.md`
- `progress/charles/006-2B-WORLD-ACCEPTANCE.md`
- `progress/charles/006-3-WORLD-ACCEPTANCE.md`
- `progress/charles/006-4-ACCEPTANCE.md`
- `progress/charles/006-5-CLI-ACCEPTANCE.md`
- `progress/charles/006-FINAL-DEMO-ACCEPTANCE.md`
- `progress/charles/006-FINAL-INTEGRATION-ACCEPTANCE.md`
- `progress/charles/006-INTEGRATION-AUDIT.md`
- `progress/charles/006-INTEGRATION-WORLD-ACCEPTANCE.md`
- `progress/charles/006-MAIN-MERGE-ACCEPTANCE.md`
- `progress/charles/006-SESSION-ACCEPTANCE.md`
- `progress/charles/CONTRACT_REQUEST.md`
- `progress/charles/PROGRESS.md`
- `progress/charles/SONNY-FINAL-ENGINE-FIX.patch`
- `progress/charles/SONNY-FINANCIAL-HANDOFF.md`
- `progress/charles/SONNY-UNBLOCK-ACCEPTANCE.md`
- `progress/charles/SONNY-WORLD-HANDOFF.md`
- `progress/sonny/CONTRACT_REQUEST.md`
- `progress/sonny/PROGRESS.md`
- `progress/sonny/SESSION-HANDOFF.md`
- `recoup/app.py`
- `recoup/cli.py`
- `recoup/contracts/capabilities.py`
- `recoup/contracts/interfaces.py`
- `recoup/contracts/models.py`
- `recoup/contracts/remittance.py`
- `recoup/contracts/testing.py`
- `recoup/contracts/tools.py`
- `recoup/engine/AGENTS.md`
- `recoup/engine/config.py`
- `recoup/engine/counteroffers.py`
- `recoup/engine/derive.py`
- `recoup/engine/factory.py`
- `recoup/engine/gates.py`
- `recoup/engine/harness.py`
- `recoup/engine/ingest.py`
- `recoup/engine/llm/__init__.py`
- `recoup/engine/llm/fake.py`
- `recoup/engine/llm/openai_compat.py`
- `recoup/engine/llm/replay.py`
- `recoup/engine/policy.py`
- `recoup/engine/prompts/system_v1.md`
- `recoup/engine/readiness.py`
- `recoup/engine/rules.py`
- `recoup/engine/scans.py`
- `recoup/engine/scheduler.py`
- `recoup/engine/tools.py`
- `recoup/world/__init__.py`
- `recoup/world/clock.py`
- `recoup/world/hashing.py`
- `recoup/world/ids.py`
- `recoup/world/ledger.py`
- `recoup/world/lines.py`
- `recoup/world/remittance.py`
- `recoup/world/store.py`
- `tests/app/__init__.py`
- `tests/app/conftest.py`
- `tests/app/doubles.py`
- `tests/app/test_build_integration.py`
- `tests/app/test_config_unit.py`
- `tests/app/test_engine_acceptance.py`
- `tests/app/test_facade_unit.py`
- `tests/app/test_factory_unit.py`
- `tests/app/test_final_integration.py`
- `tests/app/test_financial_intake.py`
- `tests/app/test_human_escalation_acceptance.py`
- `tests/app/test_mutations_integration.py`
- `tests/app/test_regression_unit.py`
- `tests/app/test_scoped_controller.py`
- `tests/cli/conftest.py`
- `tests/cli/test_engine_workflows.py`
- `tests/cli/test_financial_intake.py`
- `tests/cli/test_routing.py`
- `tests/cli/test_sqlite_workflows.py`
- `tests/contracts/test_capabilities.py`
- `tests/contracts/test_design_contract.py`
- `tests/contracts/test_financial_extensions.py`
- `tests/contracts/test_models.py`
- `tests/engine/__init__.py`
- `tests/engine/doubles.py`
- `tests/engine/fixtures.py`
- `tests/engine/test_007_3_integration.py`
- `tests/engine/test_007_4_integration.py`
- `tests/engine/test_007_5_integration.py`
- `tests/engine/test_007_8_integration.py`
- `tests/engine/test_counteroffer_harness.py`
- `tests/engine/test_doubles.py`
- `tests/engine/test_harness_factory_ingest.py`
- `tests/engine/test_offer_ref_acceptance.py`
- `tests/engine/test_openai_compat.py`
- `tests/engine/test_policy_readiness.py`
- `tests/engine/test_rules.py`
- `tests/engine/test_scan_ingest.py`
- `tests/engine/test_scheduler.py`
- `tests/engine/test_tools_gates_derive.py`
- `tests/engine/test_vectors.py`
- `tests/engine/tool_support.py`
- `tests/engine/vectors/README.md`
- `tests/engine/vectors/amendments.json`
- `tests/engine/vectors/boundaries.json`
- `tests/engine/vectors/damage.json`
- `tests/engine/vectors/early_pay_discount.json`
- `tests/engine/vectors/hero.json`
- `tests/engine/vectors/intake.json`
- `tests/engine/vectors/late_delivery.json`
- `tests/engine/vectors/nonpayment.json`
- `tests/engine/vectors/pricing.json`
- `tests/engine/vectors/promo_rebate.json`
- `tests/engine/vectors/returns.json`
- `tests/engine/vectors/shortage.json`
- `tests/engine/vectors/trust.json`
- `tests/engine/vectors/unexplained_short_pay.json`
- `tests/world/conftest.py`
- `tests/world/test_actions.py`
- `tests/world/test_core.py`
- `tests/world/test_counteroffer_boundary.py`
- `tests/world/test_engine_boundary.py`
- `tests/world/test_fixtures.py`
- `tests/world/test_identity.py`
- `tests/world/test_remittance.py`
