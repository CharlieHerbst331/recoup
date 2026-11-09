# Charles prerequisites for Sonny — 2026-11-09

Charles's shared-contract, World, app and CLI prerequisites are complete. The
implementation is published on `006-2b-sqlite-world-core-and-app-build`; the final
implementation candidate SHA is recorded below after the implementation commit.
This branch incorporates Sonny's repaired engine at
`9c821adb23d645eea0173ad42900e23d8574ff4e` by fast-forward, then adds Charles-owned
changes. No Sonny engine, Carter UI/bench, dependency manifest, Makefile or AGENTS
file was edited for this task.

## Resolutions and remaining ownership

The normative definitions are exclusively in `docs/design/02-technical-design.md`.
The following references close the contract requests; Sonny still implements or
checks his consumers, rather than treating a shared definition as engine acceptance.

| Sonny request | Approved shared seam | Sonny's remaining consumer work |
|---|---|---|
| Negative deductions / needs-human | §5.3 engine-local escalation exception and actual case status | Verify tool/harness handling without invented monetary verdicts. |
| Explicit legal review | §3.7 / §5.3 cited legal-review vocabulary | Implement/check flag routing, conflicting/untrusted signals and authority inventory. |
| Buyer-email classification | §3.7 canonical line/reason fields and `FactSet.buyer_senders` | Consume sender metadata in pure rules/readiness; append cited classification facts when needed. Scheduler buyer-reply detection must use both allowed email and portal recipients. |
| FactSet citation validity | §3.7 World grounding guarantee and consumer rechecks | Re-resolve current citations at tool/gate boundaries; pure consumers use the World-provided effective basis. |
| Selected-case execution | §3.5 / §4.5 additive `ScopedController` | Default app adapter is implemented; custom controllers add scope only if selected-case execution is needed. |
| Event / due ordering | §5.7 confirms existing scheduler order | Verify equal-time event/due ordering; no new sequence field or contract request needed. |
| Doctor / scans | §5.8 shared local capability helper | Re-export/delegate `recoup.contracts.capabilities.scan_capabilities` from owned scan code; retain honest unavailable extraction behavior. |
| Counteroffers | §3.7–3.8 / §5.4–5.5, shared selector and persistence defense | Implement 007-8 derivation, semantic gates, tools, completion/FakeLLM and event paths; engine tests cover full approval/mock-send behavior. |
| Multi-invoice remittances | §3.9 typed intake, World, app, CLI and examples implemented | Consume normal invoice-specific balances and verify existing handler investigation after intake. No separate allocation algorithm is needed. |

Counteroffer financial policy, shared models and World defenses belong to Charles;
the executable engine derivation/tool/gate path belongs to Sonny. Historical
multi-invoice allocation is implemented in Charles's World/app/CLI domain.
**None of these remaining Sonny tasks depends on Carter's implementation.**

The focused owner handoffs are `SONNY-FINANCIAL-HANDOFF.md` and
`SONNY-WORLD-HANDOFF.md` in this directory. Task 007-8 is updated in the engine spec.

## Acceptance

- `make check`: lint and formatting pass; **969 passed, 2 optional OCR skips**.
- Actual installed engine `recoup --db :memory: check-regression`: **8/8 PASS**.
- Complete World suite: **145 PASS**, covering cash conservation, atomic rollback,
  duplicate bank cash, conflicting source revisions, replay/restart, quarantine,
  offer authority/line/balance limits, exact approval selector binding, lifetime
  receipt reservations and grounded citations.
- Actual two-case app assembly proves selected-case isolation, unrelated pending
  event/due preservation, rollback after engine failure and scope restoration.
- The real app/CLI remittance example persists invoice balances and audit, retains
  explicit unapplied cash and replays without another ledger payment or callback.
- The counteroffer example loads and produces a proven disputed deduction with
  resolving cited buyer offer facts. It is a runnable prerequisite fixture; the
  existing engine counteroffer path remains Sonny's next implementation.
- `doctor` reports pypdf/Pillow/pytesseract and pdftoppm present, tesseract absent,
  fake mode and vision unavailable in this environment. No provider/network check,
  software installation or live-model spend was performed.
- Independent subagent source review and focused tests found no remaining material
  Charles-side issue. `git diff --check` passes.

The two skips require the optional tesseract executable. Historical persisted
FactSets from before the additive `buyer_senders` field keep its empty default and
fail closed. Unsupported old fact revisions are exposed as errors instead of
silently repairing immutable evidence; those legacy revisions require an explicit
data migration as explained in the World handoff. No automatic migration was run.

This is an additive contract candidate superseding the original
`89675c0b6ac676fa28c3475f58134689b74c274c` baseline for the shared extensions. It
does not create a `contract-v1` tag, imply formal independent F0 acceptance or
claim Sonny's remaining engine implementation is finished.

## Continue on Sonny's existing branch

Fetch and merge the published Charles branch, preserving Sonny's owned changes:

```sh
git fetch origin
git merge origin/006-2b-sqlite-world-core-and-app-build
```

Then continue the remaining engine consumers listed above through offline
acceptance. Run `make check`, the eight regression cases and the H/C/N integration
checks. Any new implementation defect should identify the concrete source/test;
the financial and orchestration definitions no longer require guessing or a new
Charles decision. No collaborator permission change is needed for the shared
remote that Sonny already uses.

## Changed files

The complete Charles change list is appended below before publication. Original
untracked `arhcive/` and `recoup-006-charles-bundle-r10.md` were preserved and
excluded from the commit.

- `cases/ambition/README.md`
- `cases/ambition/counteroffer/bundle.json`
- `cases/ambition/multi-invoice/remittance.json`
- `docs/design/02-technical-design.md`
- `docs/specs/007-sonny-engine.md`
- `progress/charles/CONTRACT_REQUEST.md`
- `progress/charles/PROGRESS.md`
- `progress/charles/SONNY-FINANCIAL-HANDOFF.md`
- `progress/charles/SONNY-UNBLOCK-ACCEPTANCE.md`
- `progress/charles/SONNY-WORLD-HANDOFF.md`
- `recoup/app.py`
- `recoup/cli.py`
- `recoup/contracts/capabilities.py`
- `recoup/contracts/interfaces.py`
- `recoup/contracts/models.py`
- `recoup/contracts/remittance.py`
- `recoup/contracts/testing.py`
- `recoup/contracts/tools.py`
- `recoup/world/remittance.py`
- `recoup/world/store.py`
- `tests/app/doubles.py`
- `tests/app/test_factory_unit.py`
- `tests/app/test_financial_intake.py`
- `tests/app/test_mutations_integration.py`
- `tests/app/test_scoped_controller.py`
- `tests/cli/test_financial_intake.py`
- `tests/cli/test_routing.py`
- `tests/contracts/test_capabilities.py`
- `tests/contracts/test_design_contract.py`
- `tests/contracts/test_financial_extensions.py`
- `tests/contracts/test_models.py`
- `tests/world/test_counteroffer_boundary.py`
- `tests/world/test_remittance.py`
