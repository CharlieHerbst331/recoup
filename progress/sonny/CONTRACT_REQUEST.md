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
