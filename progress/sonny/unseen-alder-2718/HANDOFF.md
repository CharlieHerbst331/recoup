# Single unseen-case generation and evaluation handoff

Authorized by the user's current request; one step only. SYNTHETIC data,
MOCK actions, offline validation LLM fake, separate manual evaluation LLM live.

Edit allowlist:
- cases/unseen/alder-2718/bundle.json
- tests/engine/test_unseen_alder_fixture.py
- progress/sonny/unseen-alder-2718/** (evaluator checklist, manual evaluation
  runner, immutable captured artifacts, verification output and assessment)
- progress/sonny/PROGRESS.md (append three lines only)

Remote allowlist: the identical new bundle under /data/app/cases/unseen/alder-2718;
evaluation runner/artifacts under /data/app/progress/sonny/unseen-alder-2718;
normal application writes for this case to /data/recoup.db and new immutable
responses in /data/app/runs/recordings. No approval or submission calls.
Existing case contents, source, dependencies, rules, harness, UI and recordings
are outside the editing scope. Existing dirty work is preserved.

Read sources: root AGENTS.md; current recoup/contracts bundle, models, money,
interfaces, tools, resolve, remittance, capabilities, oracle and testing;
design/01 §6–11; design/02 §2, §3.1–3.9, §4.5, §5.1–5.10, §6, §8.1;
existing bundle fixtures, app.load/build, engine ingestion/rules/harness/scheduler,
live adapter/recorder and shared-backend handoff. Normative definitions remain
in design/02; this handoff grants no implementation changes.

Evaluator checklist is separate from the bundle and is never passed to World,
tools or the model. Validate through app.build with in-memory SQLite, offline.
Run make check before the manual live load. Use existing live server environment
and normal app.load; let the unchanged harness choose tools. Capture history and
requests/results in stored order, compare only after the run, preserve all stops.

Pre-run fixture compatibility: the existing shared World requires start_date
2026-10-20 (design/02 §4.4). The fixture uses that required epoch with new
September/October transaction dates; no clock mutation is authorized.

Observed hosting variation: React default /data/react-recoup.db is also an
authorized normal-application output for the same case. Its separate failed
attempt is preserved in live-app; the original actual live run is opened in
the browser through Open saved run, without copying or seeding decisions.
Prior browser selection: /data/react-runs/simulation-f37f2ea546704c2da82289f3e90e52e5.db.
Remote source/artifact transfer chunks remain evaluator-only under this folder.
