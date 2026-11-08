# Sonny rule vectors

SYNTHETIC fixture data for spec 007, step 007-0. References: bundled design/02 §3.7 and §5.3; hero snapshots reference design/01 §10.

These JSON files are authoring fixtures, not serialized contract models. The owner-local factories in `tests/engine/fixtures.py` adapt them to the pinned candidate contracts per external r10 design/04 §3. No production implementation or contract type is included.

Each file has a local `fixture_format`, `provenance`, `stage`, and `vectors` list. Each vector has a unique `id` and a source `reference`.

- `input.documents` holds source document IDs, kinds and flat vocabulary fields. Documents without explicit ingestion metadata represent readable structured inputs with source trust. `readable`, `trust`, and `confirmed` are fixture adapter hints.
- `input.line` holds the rule's target line. Its values correspond to the selected source deduction's `ded.<n>.*` fields; these fixtures do not reproduce an entire intake bundle.
- `input.ledger` is optional authoring data for the prior-credit scenario. Its `event` label maps to `LedgerEntry.kind`.
- `expected_finding` is a subset assertion. Optional `flags_include`, `cite_documents_include`, `missing`, and `note_contains` constrain the resulting finding without prescribing contract serialization.
- `expected_route` and `downstream_reference` describe later integration checks, outside the pure rule finding. They are not rule inputs.
- `intake.json` targets deduction intake separately and asserts only added synthetic lines with `expected_added_lines`; existing deduction lines are not included in that list. Its `input.now` is the simulated date.

Coverage:

| File | Fixture IDs / scope |
| --- | --- |
| early_pay_discount.json | early_on_boundary, early_after_window, early_missing_paid_date |
| pricing.json | pricing_partial, pricing_missing_price, pricing_same, pricing_higher, pricing_zero, gross_basis_prior_credit |
| late_delivery.json | late_after_grace, late_grace_boundary, late_on_time, late_missing_delivery, late_pod_tracking_conflict, late_po_precedes_contract, late_tracking_fallback |
| damage.json | damage_window_boundary, damage_missing_inspection, damage_outside_waiver_*, damage_refused_pod, damage_deduction_date_precedence |
| shortage.json | shortage_partial, shortage_missing_pod, shortage_unsigned_pod, shortage_seller_short_shipped |
| returns.json | returns_received_cap, returns_line_qty_cap, returns_required_no_rma, returns_unreadable_rma, returns_missing_* |
| promo_rebate.json | promo_earned_partial, promo_not_earned, promo_missing_* |
| unexplained_short_pay.json | u1_requests_reason |
| nonpayment.json | np_balance_owed, np_missing_pod, np_unsigned_pod |
| boundaries.json | tolerance_claimed_* (seven cases), negative_claimed |
| amendments.json | amendment_authorized, amendment_unauthorized_role, amendment_future, amendment_latest_effective, amendment_same_date_conflict, amendment_missing_author |
| trust.json | pricing_unconfirmed_ocr, pricing_confirmed_ocr, pricing_unconfirmed_vision, pricing_confirmed_vision |
| hero.json | hero_d1_before_pod_v2, hero_d1_after_pod_v2, hero_d2_before_pod_v2, hero_d2_after_pod_v2 |
| intake.json | u1_paid_gap, np_zero_paid_no_deductions, np_no_payment_doc, np_due_date_not_overdue, zero_paid_with_deduction_is_u1, zero_paid_fully_explained_no_np, u1_subtracts_prior_credit, u1_at_tolerance, u1_above_tolerance, not_overdue_no_activity |

Persistent checks in `tests/engine/test_vectors.py` validate data and typed input construction. Rule execution remains 007-1; actual World/engine replay remains BLOCKED pending providers at G1/G3 (external r10 design/04 §2–5). The negative-claimed expectation is a case escalation expectation, not a RuleFinding verdict; the contract has no needs_human Verdict. No replacement enum is introduced.
