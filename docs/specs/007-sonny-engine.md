# 007: Engine (owner: Sonny)
**Status:** design review pending. **Supersedes:** specs/002 (kept). **Design:** design/02 §3.4–3.5, §3.7, §5. Your categories A–E map to design/01 §5.

## Owns
- `recoup/engine/**` (including `AGENTS.md`, `factory.py`, `prompts/`, `llm/`)
- `tests/engine/**`
- `progress/sonny/**`

**Never touch:** contracts, world, app, cli, ui, bench, cases, pyproject. Send contract requests to `progress/sonny/CONTRACT_REQUEST.md` and dependency requests to Charles.

## Steps
**0. Pre-F0 (data only, no recoup imports):** write `tests/engine/vectors/*.json`. Each vector holds facts in the §3.7 vocabulary plus the expected finding. Cover every reason, including the missing, contradiction and unauthorized cases, plus gross-basis prior credit (§5.3 example), U1 vs NP, and hero D1 before/after POD v2 and D2. Also create `recoup/engine/AGENTS.md` from harness/AGENTS-engine.md and `progress/sonny/PROGRESS.md`.

**007-1 (after G0): rules + flags.** File `rules.py`: `run_rules(lines, facts: FactSet, ledger) -> list[RuleFinding]` (signature in design/02 §3.7 "Inputs"), following the §5.3 table exactly. Tests:
- the §5.3 tolerance boundary vectors, asserting verdict and money agree (invalid ⇒ disputed > 0; valid ⇒ disputed = 0), plus claimed 0 and negative claimed;
- a money fact present only as a confirmed `origin=fact` EffectiveFact is used, and the finding cites `fact:<fact_id>`;
- returns, with RMA required: no `return_auth` in `facts.docs` → proven 0; an attached unreadable `return_auth` (zero facts) → needs_info; a readable one without `received_qty` → needs_info;
- legal: a readable `legal_authority` doc present vs absent changes needs_human;
- every vector;
- invariants: 0 ≤ valid ≤ claimed and valid + disputed = claimed when proven; needs_info → both None;
- rules ignore prior credits (gross valid); credits are subtracted only in derive (§5.3 example);
- tolerance;
- precedence of authorized amendments;
- a same-date amendment conflict → contradiction;
- an outside-window damage claim without a waiver → unsupported_terms;
- nonpayment → invalid plus follow_up path.

**007-2 (after G0): policy + readiness.** Files `policy.py` and `readiness.py` (pure `readiness.dispute/notice/claim`, signatures in design/02 §3.7 "Inputs"), per §5.6. Tests:
- two lines sharing one FactSet: line A (proven invalid, cited facts confirmed) → dispute-ready; line B (finding with a contradiction or an unconfirmed ocr fact) → not_ready; each Readiness has its own `line_id`;
- a mismatched `finding.line_id` raises ValueError;
- claim items use the fixed §5.6 `claim.*` ids;
- `policy.answer(claim_window)`: identical facts with two notice receipt dates give two claim_open dates; no receipt → missing_evidence;
- `policy.answer(exclusions)` returns `list[PolicyAnswer]`: an exclusion present only in policy text → one missing_evidence answer until a cited `exclusion.<i>` fact is accepted, then one answer with that fact's citation; two exclusions (one `fields.` source, one `fact:` locator) → two answers whose distinct citations survive `CheckPolicyResult` JSON round-trip;
- `readiness.notice`, with applicability, trigger, deadline and balance established:
  - (a) a deduction line needs_info (missing POD) → notice `ready`, dispute_status `unknown` with the line noted;
  - (b) only a nonpayment finding (invalid) → dispute_status `present` ("no buyer dispute");
  - (c) a deduction line proven invalid with `excluded_until_resolved` → `restricted`, notice still `ready`;
  - plus: unknown applicability (no covered_buyer fact) → not_ready;
- `claim.doc.pod` with otherwise identical facts: no POD → missing; attached unreadable POD (zero facts) → defective; readable unsigned → defective; readable signed → present;
- P-A-like vs P-B-like produce different deadlines and restrictions;
- claim checklist statuses;
- no eligibility field;
- a missing POD does not block the notice.

**007-3 (after G1): tool session, gates, derivation.** Files `tools.py` (`ToolSessionFactory`, §3.4–3.5), `gates.py` (ProposalValidator, including the assertion check), `derive.py` (§5.4). Integration tests get the world from `app.build(RecoupConfig(db=":memory:")).world` (design/02 §2 test-import table; never import `recoup.world`):
- propose_fact accepts a value found in the quote and rejects a fabricated one;
- a superseded citation is rejected;
- an excessive edited credit is rejected;
- an unsupported edited dispute is rejected;
- assertion check: fails an affirmative claim; passes a negated caveat, a quoted policy phrase and "cash collected: $0";
- hero derivation, including correction + incremental credit (design/01 §10 numbers);
- correction/supplement keys `:<n>` per §3.8; receipt-level correction allocation per §5.4: original 100 + supplement 20, new disputed 30 → corrections 20 (supplement) + 70 (original), net 30; then a second evidence change to 10 → one more correction 20 on the original;
- dispute readiness per line (§5.6): one blocked line leaves the others ready;
- readiness tool: dispute without line_id → `line_id_required`; notice with line_id → `line_id_not_allowed`; unknown line → `unknown_line`;
- `static_output` exports `claim_items` from claim readiness (§8.1).

**007-4 (after G2): harness + FakeLLM + ReplayLLM + factory.** Files `harness.py`, `config.py`, `prompts/system_v1.md`, `llm/{__init__,fake,replay}.py`, `factory.py` (`build_engine`, `get_llm`, `harness_controller`; §4.5), `ingest.py` (text, structured, text_pdf, and the failure statuses). Tests:
- hero day-0 results;
- a mixed-evidence insured case with a missing POD on one line still produces the other line's proposals and the notice readiness;
- `end` is refused until completion;
- loop guard;
- a ScriptedLLM that sends a wrong verdict on a proven line is overridden;
- a text PDF generated inside the test is usable.

**007-5 (after G2): handlers.** File `scheduler.py`, per §5.7. Tests:
- advance to day 3 → correction + incremental credit with no repost;
- buyer silence → exactly one follow-up;
- a buyer email cancels the pending follow-up;
- notice at deadline − 7;
- the claim window drafts the claim package;
- after a restart, the second handle adds nothing;
- an exception mid-event rolls back its proposals and leaves the event unprocessed (§5.7 transaction).

**007-6: live adapter.** File `llm/openai_compat.py`. Read the official OpenAI Python SDK tool-calling docs first, and record the URL and date in `progress/sonny/PROGRESS.md`. Recording goes to ReplayLLM. Tests use a stub client and no network.

**007-7: OCR path (SHOULD).** Use tesseract via pytesseract when `doctor` finds it; fields get `ocr` trust. Add the vision path (AMBITION). Tests are skipped when the tool is unavailable, and there is always an `ocr_unavailable` test.

**007-8: ambition (shared seams approved 2026-11-09).** Implement the counteroffer engine derivation, gates, tools and FakeLLM/handler behavior against design/02 §3.7–3.8 and §5.4–5.5, using the imported `offer_ref` contracts. Add engine integration coverage for positive boundary, missing/conflicting/expired/untrusted evidence, nonpayment exclusion, cumulative receipt reservations, downward edits, stale approval revalidation, duplicate submissions and concurrent approved offers. This completes Sonny's remaining engine work; the Charles World guard is defense in depth, not a replacement for engine derivation.

Multi-invoice historical remittance intake belongs to **Charles's contracts/World/app/CLI** under design/02 §3.9; Sonny's engine consumes the resulting ordinary cases and payment ledger through the existing World port. Sonny adds app-built multi-invoice rule/handler integration coverage and any normal re-investigation handling needed after intake; do not create a parallel allocation implementation or an external settlement action. Charles supplies the shared models, transactional intake and loader wiring. Carter has no prerequisite implementation for either feature.

The remaining shared decisions in `progress/sonny/CONTRACT_REQUEST.md` are resolved normatively in design/02: escalation/legal/buyer-email classification and citation validation (§3.7, §5.3), selected-case routing (§3.5, §4.5), event/due ordering (§5.7), and optional scan/doctor prerequisites (§5.8). Sonny should verify the existing owned consumers against those sections and finish any owned adapter gaps; no further invented contract seam is required.

## Acceptance
- `make check` is green with no network.
- Every test listed above passes.
- The model can never set money or override a proven verdict.
- FakeLLM is labeled `mode=fake` in traces.

