# 008: Workbench UI + benchmark (owner: Carter)
**Status:** design review pending. **Supersedes:** specs/003 (kept).
**Design:** design/01 §3, §6–§11; design/02 §6, §8. Metrics, accounting and logs are normative in design/02 §8.6. Bench rev 3 is background only.

## Owns
- `recoup/ui/**` (incl. AGENTS.md)
- `recoup/bench/**` (incl. AGENTS.md, `prompts/tmin_v1.md`)
- `bench/dev/**`, `bench/episodes/**`, `bench/PLAN.lock`, `bench/prices.json`, `bench/results/**`
- `tests/ui/**`, `tests/bench/**`, `progress/carter/**`

**Never touch:** contracts, world, app, cli, engine, `cases/**`, `bench/holdout/**` (don't open its oracles until scoring), pyproject.

## Steps
1. **Pre-F0 (data only):** write 8 static dev bundles (`bench/dev/static/sNN/bundle.json`) and 8 episode dev scenarios (`bench/episodes/dev/eNN/bundle.json` with events), C1–C4 × 2, in the §3.3/§3.7 formats. Keep their oracles in `bench/dev/oracle/` and `bench/episodes/dev/oracle/`, formatted per §8.1, each with a sentinel. Coverage:
   - static: valid 2, invalid 2, partial 2, needs_info 2, ≥ 2 traps;
   - episodes: C2 includes a POD v2 supersede after a submit; C4 includes one missing and one defective claim doc.
   - Also create `recoup/ui/AGENTS.md` and `recoup/bench/AGENTS.md` from harness/AGENTS-ui-bench.md, and `progress/carter/PROGRESS.md`.
2. **008-1 (after G0): static scorer + validator.**
   - `score_static.py` and `summarize.py`, per design/02 §8.1 and §8.6.
   - `validate.py`: counts, cents reconciliation, refs exist, acceptable ⊇ required, sentinels absent from inputs.
   - Implements every §8.6 static component and safety failure using only `StaticRunRecord` (context, inventory, facts, bases, model_requests); historical citations go through `contracts.resolve.resolve_citation` with the matching `bases` entry.
   - Tests: gate oracle replay (`cases/regression`, once Charles merges them) scores 8/8; the six §8.6 required tests (incl. one wrong claim item status → strict fail); each corruption fails its intended check; output is byte-identical across runs.
3. **008-2 (after G1): workbench UI** (`recoup/ui/app.py` + `view_helpers.py`), per design/02 §6. Tests via pure helpers on `recoup.app.build(RecoupConfig(db=":memory:"))` with a loaded demo bundle (design/02 §2: ui imports contracts and app only):
   - stale disables submit;
   - no total row;
   - the provenance banners are present;
   - edit diffs render;
   - the quarantine list renders.
4. **008-3 (after G2): Track T world driver.**
   - `bench_tools.py` (`BenchSession`, design/02 §3.4), `approver.py`, REF and BAD-* controllers, all through `recoup.app` (§8.3).
   - `score_episode.py`.
   - A visibility self-test and a leakage test (§8.4).
   - Tests: a falsely claimed quarantine is scored wrong (uses `StaticRunRecord.load`); a rejected write counts as `unsafe_attempt`; an `idempotent_return` retry is not a duplicate; a `fact:<id>` citation resolves via the record's `facts` (static) or `history.facts` (episode); a sentinel only inside a tool error or only inside a model request is caught; a T-min run never calls the harness (§4.5 test); the Track S inventory hashes are equal for P-M and H-M.
5. **008-4 (after G3): T-min + runners.**
   - `prompts/tmin_v1.md`: freeze and commit it **before** any H-M tuning.
   - Tests: same bundle with `static_day` before vs after the due date → both arms' `context`/`input_sha256` differ and NP appears only after in both arms' output; zero model/controller calls before the freeze; no events or future docs released by the calendar-only advance; H-M's first model request shows `context.sim_now`; claim_items are computed at `context.sim_now`; an episode citation against an old basis after a revision resolves from `EpisodeRunRecord.bases` alone.
   - `tmin.py`, `run.py`, `serialize.py` (the P-M prompt includes the StaticOutput schema with `claim_items` and the §5.6 claim item ids, design/02 §8.2).
   - Arms: R0 (`Recoup.rules_only`)/F0/P-M/H-M (Track S, frozen inventory test §8.2) and REF/BAD/T-min/H-M (Track T, injected controllers §8.3), with one outer budget.
   - Logs and the CSV/summary.md export.
   - `prices.json` rows need a URL and date_read; an unknown price fails closed.
   - With no key → NOT EVALUATED. No live run without Charles's approved budget.
   - `PLAN.lock` is committed before the first live run.
6. **008-5 (optional):** target tier of 28 episodes, plus C5/C6.

## Acceptance
- `make check` green offline.
- REF passes, and every BAD controller fails its intended check.
- The leakage test passes.
- Offline arms complete; live arms show NOT EVALUATED when there's no key.
- The T-min prompt commit predates any harness tuning commit.
- The UI tests pass.

