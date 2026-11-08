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
