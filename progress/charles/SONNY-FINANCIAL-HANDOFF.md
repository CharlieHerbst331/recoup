# Sonny unblock handoff — 2026-11-09

Charles authorized the shared decisions and interfaces in this candidate. The
normative definitions live in [design/02](../../docs/design/02-technical-design.md),
not in this handoff. This document identifies implementation ownership and the
remaining verification work.

## Shared decisions and ownership

| Request | Resolution and owner |
|---|---|
| Negative amounts and human escalation | Approved engine-local exception/consumer handling, design/02 §5.3; Sonny verifies the consumers. |
| Legal-review routing | Explicit cited routing vocabulary, §3.7 and §5.3; Sonny implements/validates rules and adapters. |
| Buyer-email reason classification | Canonical reason vocabulary and sender validation, §3.7; Sonny verifies tools/rules integration. |
| Pure readiness citation boundary | World validates FactSets, consumers re-resolve current citations, §3.7; Charles owns World, Sonny owns consumer checks. |
| Selected-case runs | Additive controller scope, §3.5 and §4.5; Charles owns app/default adapter. Existing `Controller.react` stays compatible. |
| Cross-kind event/due order | Existing scheduler fallback approved as the canonical ordering, §5.7; no new sequence model required. |
| Doctor/scan reporting | Optional system renderer approved and shared contracts capability probe, §5.8; Charles owns CLI composition, Sonny owns backend extraction. |
| Counteroffers | Shared selector contracts plus normative derivation/gates, §3.7–3.8 and §5.4–5.5; **Sonny owns engine derivation/gates/tools/handlers**, Charles owns World defense and shared contracts. |
| Multi-invoice allocation | Historical intake, §3.9; **Charles owns contracts/World/app/CLI**. Sonny consumes normal cases/payment ledgers and verifies handler integration. |

Carter is not a prerequisite for these implementations. Existing custom controllers
need the additive scope only when callers request a selected-case run; ordinary
react signatures remain unchanged.

## Import these shared contracts

- `recoup.contracts.models`: `Proposal`, `Approval`, `Receipt` carry optional
  `offer_ref`, defaulting to `None` for old serialized data.
- `recoup.contracts.tools.DraftProposalArgs` carries the same selector; there is
  still no model-controlled amount or allocation input.
- `recoup.contracts.remittance`: `RemittanceBundle`, `RemittanceAllocation`,
  `CasePaymentAllocation`, `RemittanceLoadResult`.
- `recoup.contracts.models.FactSet.buyer_senders`: World-provided sender allowlist for pure buyer-email classification.
- `recoup.contracts.capabilities.scan_capabilities`: shared local probe; re-export/delegate from the owned scans module to prevent doctor/backend drift.
- `recoup.contracts.interfaces`: use the updated actual World/controller ports;
  do not duplicate models or signatures locally.

## Sonny's remaining implementation/acceptance lane

Implement 007-8's counteroffer path in the owned engine files following design/02
§5.4–5.5. Extend the owned completion/FakeLLM/handler paths as necessary so an
explicit supported buyer offer can actually be drafted and sent through approval
and mock submission. Ensure legacy cases with no offer continue to work. The
Charles World guard intentionally rejects unsafe payloads even before this engine
path exists; that guard does not implement the model/tool derivation for Sonny.

Use app-built in-memory World integration tests. Cover authority equal/below/over
boundary; missing/conflicting/untrusted authority; line and open-balance caps;
unsupported/nonpayment lines; missing/expired/conflicting offers; trusted buyer
identity; exact selected reference/line punctuation; per-line and lifetime
reservations across receipts; downward edits with zero line allocations; stale
basis/decision/expiry at approval and submit; duplicate mock submission and offer-reference replay across different selected line sets; competing
approved offers; and immutable prior receipts. Reference the normative section
for expected financial semantics. No real send or network is required.

For remittances, consume the shared World intake and inspect invoice-specific
ledger/balance changes; do not introduce a separate engine allocation engine.
Verify that normal investigation uses those balances, unrelated invoice state is
unchanged, and the existing event handler can re-investigate loaded/changed cases.
Financial conservation, rejection/quarantine, persistence and rollback tests belong
to Charles's World acceptance lane.

Finally recheck the nonfinancial requests against the cited normative sections,
run `make check`, the eight regression cases and the full demo, and record any
owned implementation gaps honestly. Installing OCR or exercising a live model is
not required to pass the offline lane; unavailable optional paths must be reported
and tested as unavailable.

## Publication

Use the final Charles publication SHA/branch in the root acceptance report and
PROGRESS entry. It must include the shared models, normative sections and World/
app/CLI implementations together. Do not pin an intermediate working-tree state.
No engine implementation is claimed complete by this shared-contract handoff.
