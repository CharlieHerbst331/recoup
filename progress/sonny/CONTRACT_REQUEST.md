# Approval status — 2026-11-09 (America/Los_Angeles)

Requests **1–4 below are resolved by Charles's approved decisions**, published in
`933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f` (shared implementation
`75a58397bec3846847673ef8af4c7ae85d2a5264`). Normative sources are now
current design/02 §3.7 and §5.3; see
[Charles's handoff](../charles/SONNY-FINANCIAL-HANDOFF.md). The original requests
below remain as history, not current blockers. No shared changes are requested
for these four items.

The existing owned implementation uses these decisions in rules, tools, harness
and gates. Pure readiness's citation-membership boundary is approved; actual
World exposure and current consumers provide raw citation resolution. This
supersedes the former 007-2 citation-interface blocker; no additional readiness
input interface is required.

Verification of the current working tree on Nov 9:
- Legal routing, buyer-sender/line classification and human-status consumers:
  `pytest tests/engine/test_007_8_integration.py -k 'legal or buyer_classification' -q`:
  **9 passed, 39 deselected** using `/tmp/recoup-007-check/bin/python`, fake LLM.
- Current/superseded/cross-case citations, readiness isolation, actual World
  fact grounding and consumer gate rechecks:
  `pytest tests/engine/test_007_3_integration.py tests/engine/test_tools_gates_derive.py tests/engine/test_policy_readiness.py tests/world/test_counteroffer_boundary.py -k 'citation or readiness or ungrounded' -q`:
  **52 passed, 74 deselected**, same offline interpreter.

This update preserves all pre-existing uncommitted engine work and does not
commit or publish it. Other historical requests below are outside this focused
verification; their later approvals are recorded in Charles's handoff.

---

# 007-1 candidate integration questions — 2026-11-08

Candidate: `89675c0b6ac676fa28c3475f58134689b74c274c`. References: design/02
§3.2, §3.7, §5.3; external r10 design/04 §1–5. Shared files are unchanged.

1. `run_rules` returns `list[RuleFinding]`, but `Verdict` has no `needs_human`.
   Consumer acceptance: `test_every_rule_vector[negative_claimed]` requires case
   escalation with no RuleFinding money. Current owned implementation raises
   `NeedsHumanError` before evaluating any lines; it never creates a replacement
   contract verdict. Minimum requested resolution: Charles approve the exception
   boundary for the later engine consumer, or specify a shared escalation channel.
   The eventual consumer must catch it and set the actual case status; that
   integrated behavior is not claimed by these pure tests.
2. `DeductionLine`/`FactSet` supply no specified predicate identifying a line that
   requires legal interpretation. `test_legal_authority_inventory` proves the
   explicit `require_legal_authority(facts)` check distinguishes absent, unreadable
   and readable inventory. Minimum requested resolution: identify the consumer
   signal that must invoke this check; no invented field is read by `run_rules`.
   Legal document presence alone does not establish a legal conclusion.
3. The nonpayment rule excludes buyer emails classified as a dispute reason,
   but candidate `LineReasonRevision` has no evidence ID and the vocabulary does
   not specify an email classification key. The owned test uses the already
   documented `ded.<n>.reason` key on the email. Minimum requested resolution:
   confirm the actual World/consumer representation of that classification.
   Arbitrary email text is not interpreted by the pure rules.

None prevents the independent unit lane. Automatic legal routing, propagation of
case escalations and real email-classification integration remain unverified until
these consumer seams are resolved. No contract models were copied or changed.

## 007-2 citation-resolution boundary — 2026-11-08

References: design/02 §3.2, §3.7, §5.6. Candidate unchanged.

4. `readiness.dispute(line, finding, facts)` receives only `FactSet`, while shared
   `contracts.resolve.resolve_citation(c, basis, evidence, facts)` requires raw
   `list[Evidence]` and `list[FactRevision]`. `FactSet` includes neither raw text,
   pages/fields nor the backing revision citation. The pure function can check
   exact current EffectiveFact citation membership, active document membership,
   fact locator identity and trust; it cannot independently resolve the backing
   quote or revision chain. Consumer test: `test_dispute_citations_current_membership_and_resolver`
   proves current membership and separately invokes the actual shared resolver
   using hand-built evidence/revisions. It does not prove that the pure function
   re-runs raw resolution. No resolver/types were copied and no shared signature
   was changed.

   Minimum requested resolution: Charles confirm that World-produced FactSets
   contain only already-resolved effective citations, with the existing
   `World.resolve_citation` used again in the actual tool/gate consumer, or specify
   an approved input seam for raw resolution in pure readiness. Until confirmed
   and tested with actual World/tool gates, raw citation-resolution acceptance
   remains BLOCKED. This affects that check only; policy/date calculations,
   notice independence, document inventory and the other readiness predicates
   are independently implemented and tested. The existing 007-1 questions above
   remain outstanding and were not changed by this step.

## 007-5 due-work ordering seam — 2026-11-08

5. References: design/02 §3.5 and §5.7. `DomainEvent` supplies `at` and
   `seq`; `DueWork` supplies `due_at` but no `seq`, and `World.due` exposes
   no ordering metadata. Exact cross-kind `(at, seq)` ordering cannot be
   represented through the current port. Please confirm event-before-due ties
   with stable due_id ordering, or expose an approved shared sequence seam.
   The owned handler uses chronological timestamps, event seq, then events
   before due items on ties and due_id for remaining ties. This is a disclosed
   fallback, not proof of exact shared-sequence compliance. No shared model was
   edited or copied. Other independent handler behavior continues against the
   current contract; real-provider ordering acceptance remains outstanding.

Resolution — 2026-11-09: Request #5 is resolved by the approved design/02
§5.7. The scheduler now cites and uses that definition directly; the real
app-built test `test_real_event_due_ordering` verifies its ordering with reversed
provider inputs. The earlier fallback/sequence-blocker assessment above is
historical and superseded. No contract change or synthetic sequence is needed.

## 007-7 doctor/composition seam — 2026-11-08

6. Reference: design/02 §4.5 and §5.8. This checkout has no recoup.cli,
   recoup.app or doctor implementation. Charles should wire the owned
   `engine.scans.scan_capabilities(llm_mode=..., vision=...)` report into doctor
   through the allowed app composition boundary. The factory uses the same
   capability checks. No CLI/app code or shared interfaces were changed.
   OCR acceptance is not claimed while tesseract/pytesseract are absent; live
   vision acceptance is not claimed from SDK-shaped offline responses.

   Scanned PDFs additionally use an already-available optional `pdftoppm`
   executable to rasterize pages before pytesseract; the report exposes
   `pdf_renderer` separately. Missing rendering returns ocr_unavailable.
   Charles to confirm the optional system-renderer prerequisite or provide an
   approved renderer using the existing dependencies. Nothing was installed or
   added to the dependency manifests. Image OCR needs no PDF renderer.

## 007-8 ambition definition and contract seams — 2026-11-08

**Request 7 resolved — 2026-11-09:** Charles publication
`933ab052bf4ded509b4d6f8c2b7d68b38cfaea2f` includes the approved shared
`offer_ref` fields and normative counteroffer definitions in design/02 §3.7–3.8,
§5.4–5.5. The engine imports those contracts unchanged; current counteroffer
derivation, gates, tools and handler acceptance supersede request 7's historical
missing-definition/blocker statements below. Added explicit imported-model legacy
JSON/selector binding and all-stage engine gate acceptance in
`tests/engine/test_offer_ref_acceptance.py`; results are recorded in PROGRESS.md.
The original request text is retained as history.

7. Counteroffer: spec 007 step 007-8 names this feature, but design/02
   §5.4 has no counteroffer derivation and §5.5 requires allocations supported
   by that derivation. §3.7 supplies `authority_cents` and §3.8 supplies an
   identity; neither defines what the offered amount means or how code computes
   it. `DraftProposalArgs` has no negotiation input, and the model must not set
   amounts. Please add the normative derivation and gate behavior to design/02:
   whether authority caps a concession or a requested payment; the cited inputs
   selecting an offer; per-line allocation and cap scope; treatment of existing
   credits/disputes and repeated offers; and the receipt/ledger effect. Confirm
   whether the existing tool input suffices or provide the approved shared seam.
   Acceptance needs authority-boundary, missing/conflicting/untrusted authority,
   human-edit/revalidation, approval and duplicate-receipt cases against that
   definition. Current gates continue to reject counteroffers; no arbitrary
   amount formula or replacement contract was introduced.

8. Multi-invoice allocation: design/02 §3.6–3.7 defines single-invoice intake.
   `CaseBundle.invoice_ref` is singular; `LedgerEntry` and `DeductionLine` have no
   explicit invoice allocation identity. World exposes case-level ledger reads
   and no remittance-allocation write operation. Please define the normative
   remittance input, invoice/case scope, matching and ambiguity behavior,
   residual handling, conservation and duplicate/reallocation semantics in
   design/02, then confirm a representation using current contracts or supply
   the shared models/World operation and loader wiring. Acceptance needs exact
   conservation, invoice-specific balances, ambiguous/unmatched references,
   overpayment/underpayment, duplicate import and transactional rollback cases.
   A local helper or invented fact vocabulary would not establish integrated
   allocation under the current contract. No shared or other-owner files changed.

007-8 implementation is BLOCKED on these definitions. Independent prior engine
work remains intact; neither ambition feature is claimed as implemented. This
session stops at the request rather than guessing financial behavior.
