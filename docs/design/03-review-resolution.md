# Design review resolution map (2026-11-07, v9 docs)
**Status:** design review pending recheck. Nothing is done.

## Root-cause diagnosis (after two failed gates)
**Premise tested:** "a large narrative contract copied into specs and prompts is single-source enough to keep ownership, execution and benchmark semantics consistent."

**Result: false.** The r2 failures cluster where one semantic was stated in two or more places that drifted apart:
- the DAG and gates (02 §2 vs specs/handoffs);
- auto-execution (Recoup methods vs bench controllers);
- the money basis (rules vs derivation vs ledger guard);
- hashes (content hash vs the real decision basis);
- submit order (gates vs idempotent replay);
- metrics (02 vs bench rev 3).

**Missing prose volume was not the cause.**

**Structural fix (no new layers):**
1. design/02 is the **only normative source**. Each semantic has exactly one defining section (matrix below).
2. Handoff step prompts no longer restate semantics. Each says "implement PR X as specs/00N step X; normative: design/02 §…; design/02 wins; on conflict write CONTRACT_REQUEST".
3. Specs keep only ownership, steps and test lists, pointing to sections.
4. The world is neutral. Agent work happens only through an injected `Controller` (02 §3.5, §4.4–4.5), so a baseline cannot invoke the harness.
5. A docs self-check (`tools/doccheck.py`) fails on stale or duplicated phrases and on missing normative sections in each bundle.

## Consistency matrix (residual blockers 1–8 from reviews/2026-11-07-design.md, plus Verifier r2 N-B1..N-B3)
| # | Semantic | Single authoritative definition | References (cite only, never restate) |
|---|---|---|---|
| B1 | Unit of work, tool access | 02 §3.5 `World.transaction`, `ToolSession`/`ToolSessionFactory`; 02 §5.7 transaction rule; 02 §3.4 BenchSession | specs/007 (007-3, 007-5 tests), specs/008 (008-3), handoffs 007/008 prompts |
| B2 | Money basis, U1/NP, keys | 02 §5.3 ("Credits are not subtracted in rules" + example), §5.4 table, §3.8 ledger guard, §3.7 lines + vocabulary | specs/007 (007-1 test), design/01 §10 numbers |
| B3 | Immutable facts, basis hash | 02 §3.2 `FactRevision`/`LineReasonRevision`; 02 §3.6 `evidence_set_hash` definition | specs/006 (006-2 tests) |
| B4 | Submit order, correction identity | 02 §4.3 steps 1–6; 02 §3.8 key table; 02 §5.4 net-disputed rows | specs/006 (006-3 tests), specs/007 (007-3 tests) |
| B5 | Controller separation, equal inputs | 02 §3.5 `Controller`; §4.5 `build(config, controller)` + test; §8.2 frozen inventory; §8.3 controllers and budget | specs/006 (006-3 test), specs/008 (008-3/4 tests), harness/AGENTS-ui-bench |
| B6 | Scorer inputs | 02 §3.2 `ActionAttempt`, `TraceEvent.result/model_text`; §8.1 `StaticRunRecord`/`EpisodeRunRecord`, duplicate definition | specs/008 (008-3 tests) |
| B7 / N-B1 | DAG, gates, no cycle | 02 §2 DAG table, AST test rule, gates table (G1 includes app.build with stubs; 006-5 completes G3) | specs/006 (006-1, 006-2, 006-5), handoff 006 headings |
| B7 / N-B2 | Root harness | harness/AGENTS-root.md (quarantine, SqliteWorld only) pointing to 02 §3.6 | — |
| B8 | Metrics, logs | 02 §8.6 (bench rev 3 is background only, 02 header) | specs/008, handoff 008 |
| N-B3 | Dispute readiness | 02 §5.6 dispute readiness table | specs/007 (007-3 test) |

## v4 addendum to the matrix (Reviewer v3 must-fixes 1–6; the definitions were changed in place)
| # | Semantic | Single authoritative definition | References |
|---|---|---|---|
| V1 | Effective facts, locators | 02 §3.2 `EffectiveFact`/`FactSet`; §3.5 `fact_set`/`resolve_citation`; §3.7 `fact:` locator, current vs historical, citation generation, pure inputs; §3.4 `ReadEvidenceResult` | specs/006 (fact-flow test), specs/007 (007-1) |
| V2 | Scorer artifacts and checks | 02 §3.2 `TraceEvent.request`; §8.1 `StaticRunRecord` (inventory, facts, model_requests) + scan; §8.6 static components and safety | specs/008 (008-1, 008-3) |
| V3 | Receipt-level corrections | 02 §5.4 net-disputed row (newest-first allocation, worked 100+20→30 example); §3.8 per-receipt guard | specs/007 (007-3) |
| V4 | Controller-only dispatch | 02 §4.5 method comments, dispatch sentence, spy test; §6 "What runs automatically" | specs/006 (006-3) |
| V5 | Test import boundary | 02 §2 test-import table | specs/007 (007-3) |
| V6 | Tolerance and verdict | 02 §5.3 Common (order, verdict from final valid, claimed 0/negative, boundary vectors) | specs/007 (007-1) |

## v5 addendum (Reviewer v4 must-fixes 1–2)
| # | Semantic | Single authoritative definition | References |
|---|---|---|---|
| W1 | Static claim items | 02 §3.2 `ItemStatus`; §5.6 fixed `claim.*` item ids; §8.1 `StaticClaimItemOut`, `StaticOutput.claim_items`, `CaseOracle.claim_items`; §8.2 P-M prompt; §8.6 `claim_items_ok` + one-wrong-status test | specs/006 (006-4 P-B oracle), specs/007 (007-3 export), specs/008 (008-1, 008-4) |
| W2 | Pure dispute readiness inputs | 02 §3.7 "Inputs" (`readiness.dispute(line, finding, facts)`, `notice`, `claim`); §3.4 ReadinessArgs line_id rules + adapter; §5.6 dispute item table over finding/facts | specs/007 (007-2 two-line test, 007-3 tool errors) |

## v6 addendum (Reviewer v5 must-fix)
| # | Semantic | Single authoritative definition | References |
|---|---|---|---|
| X1 | Doc existence and readability for claim readiness | 02 §3.2 `DocStatus`, `FactSet.docs`; §3.7 "Inputs" (claim reads docs; input audit); §5.6 `claim.doc.<key>` mapping | specs/006 (006-2), specs/007 (007-2 four-case test) |

## v7 addendum (Reviewer batch 5)
| # | Semantic | Single authoritative definition | References |
|---|---|---|---|
| Y1 | Rules read doc inventory (RMA, legal) | 02 §5.3 returns row + Legal; §3.7 input audit table | specs/007 (007-1) |
| Y2 | Policy notice receipt and clause facts | 02 §3.7 `policy.answer(facts, q, notice_receipt)`; §3.7 vocabulary `clause.<key>`, `exclusion.<i>`; §5.6 claim_open + textual answers | specs/007 (007-2) |
| Y3 | Notice dispute status | 02 §3.7 `readiness.notice(..., findings)`; §5.6 `notice.dispute_status` | specs/007 (007-2) |
| Y4 | Basis snapshots + pure resolver | 02 §8.1 `bases`, `output_basis_hash`, `contracts/resolve.py` | specs/006, specs/008 |
| Y5 | Static calendar context | 02 §3.3 `static_day`; §3.5 `advance_to(release_events)`; §8.1 `StaticCaseContext`; §8.2 frozen static input | specs/008 (008-4) |

## v9 addendum (Reviewer v8 three contradictions; source corrected in place)
| # | Semantic | Single authoritative definition | References |
|---|---|---|---|
| Z1 | Notice independence, NP is not a dispute | 02 §5.6 notice items (4 blocking + annotation; deduction = `rule_id != "nonpayment"`); §3.2 `rule_id` | specs/007 (007-2 a/b/c) |
| Z2 | Track S neutral seed, eval-clock run | 02 §8.2 four-step frozen static input; §8.1 claim_items at `context.sim_now` | specs/008 (008-4) |
| Z3 | Typed multi-exclusion answers | 02 §3.4 `PolicyAnswer.clause_key`, `CheckPolicyResult`; §3.7 `policy.answer -> list[PolicyAnswer]`; §5.6 textual answers | specs/007 (007-2) |

## Self-check
Run `python3 tools/doccheck.py`. It checks:
- forbidden stale phrases across docs, specs, handoffs, harness and bundles;
- that each matrix anchor appears exactly once in design/02;
- that handoff prompts contain no restated normative tokens;
- that every bundle contains every normative file and section;
- that the bundle copies in assets match by sha256.

**Portable vs local:** the semantic checks (1–5) are portable and run anywhere the repo docs exist. The asset check is local-only and optional (`--assets DIR`). It reports `MISSING` or `DIFFERS` separately. A peer without access to the bot's assets path gets `SKIPPED (not accessible)`, which is not a failure.

The last result is recorded in decisions/LOG.md.

---
## History: v2 resolution map (superseded where the matrix above differs)
**Sources:** reviews/2026-11-07-design.md (Reviewer, R1–R14), verify/2026-11-07-design.md (Verifier, B1–B5), and the parent's correction list (P1–P9).
**Approach:** the docs were rewritten in place. No conflicting addenda were added.
**Status:** design review pending recheck.

| ID | Finding | Resolution (where) |
|---|---|---|
| R1 / B1 | Tool Args/Result models, World gaps | Every tool has Args/Result models, an envelope and Literal enums, and `wait_until`/`submit_approved` sit in BENCH_TOOLS (02 §3.4). World gains the following (02 §3.5): `attach_held`/held docs; `history()`; `readiness()`; `current_decision()`; injected Ingestor/ProposalValidator ports; `fail_next`; event outbox and due work; `allowed_recipients`. Composition root `app.build` (§4.5). Amount derivation (§5.4), policy answer structure, case scoping (§3.4 preamble). |
| R2 / B2 | Fact vocabulary and the 9 rules | Flat dotted-key vocabulary per DocKind, with locator resolution rules (02 §3.7). Formulas, basis-point rates, half-even rounding, clamping, tolerance, prior credits, amendment precedence and missing/contradiction/unsupported/untrusted outcomes for all 9 reasons (§5.3). Nonpayment → `invalid` + follow-up path. EUR → quarantined LoadResult and a `QuarantineRecord`, with no Money object (§3.6). The oracle carries `expected_status`. |
| R3 | Active vs superseded evidence; duplicates; closed cases | Identity, active set, hash over active evidence, rules for redelivery, superseded-citation rejection, future-doc release (02 §3.6). Closed cases reopen (02 §4.2, 01 §6). Covered by tests in specs/006 step 3. |
| R4 | Corrections MUST, with accounting | 01 §4 MUST. Derivation of incremental credit, correction and supplemental dispute, and the receipt-linked guard with no repost (02 §5.4, §3.8). Hero before/after cents, including the approved-unsent variant (01 §10). |
| R5 | Semantic gates on edits and submit | Editable fields (01 §7). The validator runs at save, approve and submit, and the ledger guard is transactional (02 §3.5, §4.3, §5.5). Tests for an excessive edited credit, an unsupported edited dispute and competing credits (specs 006/007). |
| R6 | Business idempotency | business_key, no-op/version rules, UNIQUE(business_key) on receipts, due work bound to its basis (02 §3.8, §3.2 DueWork). Restart/re-handle tests (specs 006-3, 007-5). |
| R7 | Event-to-agent lifecycle | Domain event outbox (02 §3.2). `Recoup.advance` runs day by day: `advance_to` → `engine.handle` (§4.5). Handler table covers receipts, buyer replies, policy supersession and due work, all inside transactions (§5.7). No background timers. |
| R8 | Per-line and per-track isolation | Completion criteria and the isolation rule (02 §5.6). Mixed-evidence insured test (specs/007-4). The prompt was updated (§5.10). |
| R9 | Real model capability | Model-owned judgment is defined: investigation path, line classification, cited fact extraction, rationale, info requests, drafting (02 §5.1). The live/replay proof requirement and the "not verified" wording are in 02 §10 and 01 §10 step 8. FakeLLM is labeled fallback only. |
| R10 | Track T tools and fairness | Neutral layer vs treatment-only layer, shared tools including `submit_approved`, a simulated approver, one outer budget, H-M's stricter limits disclosed, T-min prompt frozen first, BAD controllers acting through the same tools (02 §8.3). |
| R11 / B4 | Static output, oracles, leakage | StaticOutput, CaseOracle with evidence refs, EpisodeOracle, typed scorer signatures, separate scorer process (02 §8.1). Leakage test (§8.4). Data authors assigned, including 8 static dev cases by Carter (§8.5). This doc's interfaces override bench rev 3 (02 header). |
| R12 | Tier consistency | Claim readiness and corrections are MUST (01 §4). The cut order never cuts them (02 §11). Unbuilt MUST items are reported as not implemented, never replaced by REF. |
| R13 / B5 | No contract forks; ownership; DAG | No pre-F0 copies. Pre-F0 work is data only (vectors, dev bundles). Gates G0–G3 replace "any order" merging. Charles owns `docs/**`. A single SqliteWorld (`:memory:`) is used for tests, with no second World. Import-DAG test (02 §2; specs; handoffs). |
| R14 | Extraction method vs success | Separate `readable`, `method` and `failure` fields, plus per-field trust (02 §3.2, §5.8). Tests for text_pdf, ocr_unavailable and corrupt input. |
| B3 | CaseView read surface | Added `CaseHistory` (all evidence versions, decisions, proposal versions, approvals, receipts, ledger, events, traces) plus `sim_day` and `status_reason` (02 §3.2). The UI read list is in §6. |
| P1 | "Frozen" wording | Now reads "PROPOSED v1, frozen at F0 after review" in all docs. Quarantine API added. |
| P2 | Copied contracts; composition | Removed. Single composition root plus constructor-injected ports (02 §2, §4.5). |
| P3 | Oversimplified rules | Fixed: late delivery uses the required date; damage window with an explicit waiver term; shortage = invoiced − accepted on a signed POD; promo absent → needs_info; contradictions → needs_info (02 §5.3). |
| P4 | Capability strength | Claim readiness, correction and text PDF are MUST. OCR (SHOULD) and vision (AMBITION) are staged, with `doctor` checking availability. Live model proof is required to claim the capability (02 §10). |
| P5 | Word ban | Replaced with a sentence-level affirmative-assertion check that allows negated caveats, quoted policy text and factual statements (02 §5.5, 01 §8). Provenance labels added. |
| P6 | Demo correctness | Day-3 POD v2 changes D1 from invalid to valid, followed by a correction and an incremental credit. The claim example is now a missing statement of account. Timing is computed from the fixtures with `--to-next-due` (01 §10). Closed-case reopening is stated. |
| P7 | Schedule and spend | All dates are labeled unconfirmed planning targets. The holdout drop is set for ≥ 1:00 PM PT Sun, authored by the Bench bot, and marked not created/verified. No spend is authorized; budgets are proposals. Cost = returned usage × verified price (02 §8.5, §9). |
| P8 | CLI, automation, completion, simulation | `load PATH [PATH...]`. Automatic handling on advance, add-evidence and submit (02 §4.5, §6). Dual-track completion (§5.6). Sim world mutated only through World methods; the same tools for T-min; no file or oracle access (§8.3). |
| P9 | Bundles | Regenerated from these files. Every bundle carries 01, 02, 03, all harness files, and the person's spec and handoff (Charles: all specs). Copied to the bot store. No app code. |

**Still open (honest):**
- Judging rubric and demo day.
- Key and spend approval.
- Teammate acceptance and capacity.
- Bench bot holdout authoring has not started.
- "jev" is unidentified.

