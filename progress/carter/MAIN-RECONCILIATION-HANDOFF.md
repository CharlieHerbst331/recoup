# Main reconciliation — 2026-11-11 PT

One step: reconcile the published branches and the filmed React demo with
`main`, and give a reviewer a reproducible entry point. Scope for new edits:
`README.md`, `recoup/ui/DEMO_SCRIPT.md`,
`recoup/ui/frontend/src/components/dashboard.jsx`, and these Carter progress
records. Existing branch contents are integrated through Git. Behavior sources:
design/02 §3.6, §3.9, §4.2–4.5, §5 and §6–7.

`main` at `2e68776` was the first parent and `codex/enterprise-ui` at `cd26a72`
the second. The merge was clean; its tree matched the enterprise tip except for
the Charles progress entry already on main. The earlier contract, World/facade,
rule vectors, engine and Streamlit branches were already in the combined history.
The enterprise tip includes the Company Data catalog, Sonny's live-model
handling and evaluation artifacts, and both fully paid CLI fixtures. The filmed
demo's uncommitted script and queue ordering were carried over from the original
checkout. The README makes the React demo the entry point and links to tests and
the limits of the historical live evaluation. The original checkout was not used
to stage changes.

## Verification

- `make check`: Ruff lint and format passed; 1,276 tests passed and 2 skipped.
- `recoup --db :memory: check-regression` in fake mode: 8 of 8 passed.
- `node --test tests/ui/test_vercel_launcher.mjs`: 5 of 5 passed.
- The locked npm install and React production build passed. A fresh Python 3.11
  editable install, `pip check`, and `recoup doctor` passed. All 32 README file
  links resolved. No live model run or deployment was part of validation.

## Changed files relative to the previous main

- `.dockerignore` (added)
- `Dockerfile` (added)
- `README.md` (updated)
- `api/workbench.mjs` (added)
- `cases/demo/PAID-FULL/bundle.json` (added)
- `cases/demo/PAID-INSTALLMENTS/bundle.json` (added)
- `cases/unseen/alder-2718/bundle.json` (added)
- `index.html` (added)
- `progress/carter/MAIN-RECONCILIATION-HANDOFF.md` (added)
- `progress/carter/PROGRESS.md` (updated)
- `progress/carter/REVIEWER_DEMO_HANDOFF.md` (updated)
- `progress/carter/SHARED-BACKEND-HANDOFF.md` (added)
- `progress/sonny/PAID-DEMO-HANDOFF.md` (added)
- `progress/sonny/PROGRESS.md` (updated)
- `progress/sonny/unseen-alder-2718/ACTIVITY.md` (added)
- `progress/sonny/unseen-alder-2718/CHANGED-FILES.md` (added)
- `progress/sonny/unseen-alder-2718/EVALUATION.md` (added)
- `progress/sonny/unseen-alder-2718/EVALUATOR-CHECKLIST.md` (added)
- `progress/sonny/unseen-alder-2718/HANDOFF.md` (added)
- `progress/sonny/unseen-alder-2718/artifact-verification.json` (added)
- `progress/sonny/unseen-alder-2718/capture-app-attempt.tar.xz` (added)
- `progress/sonny/unseen-alder-2718/capture-initial.tar.xz` (added)
- `progress/sonny/unseen-alder-2718/live-app/chronology.jsonl` (added)
- `progress/sonny/unseen-alder-2718/live-app/drafts.md` (added)
- `progress/sonny/unseen-alder-2718/live-app/exception.json` (added)
- `progress/sonny/unseen-alder-2718/live-app/history.json` (added)
- `progress/sonny/unseen-alder-2718/live-app/manifest.json` (added)
- `progress/sonny/unseen-alder-2718/live-app/outcome.json` (added)
- `progress/sonny/unseen-alder-2718/live-app/rules-after-run.json` (added)
- `progress/sonny/unseen-alder-2718/live-app/view.json` (added)
- `progress/sonny/unseen-alder-2718/live-draft-in-app.jpg` (added)
- `progress/sonny/unseen-alder-2718/live/chronology.jsonl` (added)
- `progress/sonny/unseen-alder-2718/live/drafts.md` (added)
- `progress/sonny/unseen-alder-2718/live/history.json` (added)
- `progress/sonny/unseen-alder-2718/live/manifest.json` (added)
- `progress/sonny/unseen-alder-2718/live/outcome.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/00424b05ad32b9812e11360d7b7296412250f9a6e50d84bae2955e34f16ddc9f.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/23420bdb218f4aae3b5fb75bdfc8192a0eedf24c2e245393da95563a4e7f3533.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/3077bf18986aa524d757fb98535a4550e87f3beac2e191af8b05a5a9c1bc6ed2.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/311e91a98b04cb9c3dc6c280bf803f5e9ea8f43d6e10478f0b6bb8417126b345.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/39ef73ca07a2579da62e8605751e484344d8e6d828a358be9183a6503a54fd95.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/43932eaa72a84d08a6ad1a53e90b8c816147cdb5c26844e6e3bdd45a137ed689.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/4645028e88761c98c84b2f43e5b21df38cf09b4e7a2be459f4df8d0fa77f33e7.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/6b78e41c43f2b14c3bbd07762c910b16947906e47e1de3e2d6427ccb481ee59a.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/7b8a81f06523d845bfdfb97474b6cf53637a0a4d00bf82a8f9cd8c1abc63b404.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/91031406af6ccdea322992a56af490b5a595decb1f5e9b9936db6b5ce4ea4b37.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/9542b8031acde4c4f8c5d07396e20b4277699bf6d2022cee45bf76b27d66ce92.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/98d6c2f5923a7efc9b7697c1fbf7382ca0b56bae5527ea25efd88e5dfd44be18.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/9e65145adb2d1699a9d01b923e83a7cacefa33032b5962a00d996d64e8726860.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/9ff45caebdbe3333de3ec4a53b23a793c39883b16c8d4ff364e2d2eaa3460f54.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/a1df79435cb55c688eec8bea4c50be148d7008d14bc6e33e8924b0c7bad41273.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/b75cc51562b5234c47dcfc4f5596656f2a97f2590967690009858ad4918ab439.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/ef726dff76b5572063344190da1425c8a0e663efa355f1e00a9916a8a14ccfe5.json` (added)
- `progress/sonny/unseen-alder-2718/live/recordings/f379b5a3a17cc5eab966a21363ec54f4833c7c26833fd85b1e1541e1e0cee1e9.json` (added)
- `progress/sonny/unseen-alder-2718/live/rules-after-run.json` (added)
- `progress/sonny/unseen-alder-2718/live/view.json` (added)
- `progress/sonny/unseen-alder-2718/local-validation-manifest.json` (added)
- `progress/sonny/unseen-alder-2718/make-check.txt` (added)
- `progress/sonny/unseen-alder-2718/manual_app_live.py` (added)
- `progress/sonny/unseen-alder-2718/manual_live.py` (added)
- `progress/sonny/unseen-alder-2718/server-source-snapshot.json` (added)
- `progress/sonny/unseen-alder-2718/server-ui-source.json` (added)
- `recoup/engine/harness.py` (updated)
- `recoup/engine/llm/errors.py` (added)
- `recoup/engine/llm/openai_compat.py` (updated)
- `recoup/ui/DEMO_SCRIPT.md` (updated)
- `recoup/ui/README.md` (updated)
- `recoup/ui/__init__.py` (updated)
- `recoup/ui/api.py` (updated)
- `recoup/ui/frontend/src/App.jsx` (updated)
- `recoup/ui/frontend/src/components/audit-trail.jsx` (updated)
- `recoup/ui/frontend/src/components/case-labels.jsx` (added)
- `recoup/ui/frontend/src/components/case-page.jsx` (updated)
- `recoup/ui/frontend/src/components/company-data.jsx` (added)
- `recoup/ui/frontend/src/components/dashboard.jsx` (updated)
- `recoup/ui/frontend/src/components/workbench-sidebar.jsx` (updated)
- `recoup/ui/frontend/src/lib/ui.jsx` (updated)
- `recoup/ui/start_server.py` (added)
- `recoup/ui/workbench.py` (added)
- `tests/app/test_paid_demo.py` (added)
- `tests/engine/test_live_failures.py` (added)
- `tests/engine/test_openai_compat.py` (updated)
- `tests/engine/test_unseen_alder_fixture.py` (added)
- `tests/ui/test_react_api.py` (updated)
- `tests/ui/test_reviewer_demo.py` (updated)
- `tests/ui/test_start_server.py` (added)
- `tests/ui/test_vercel_launcher.mjs` (added)
- `tests/ui/test_workbench.py` (added)
- `tests/world/test_fixtures.py` (updated)
- `vercel.json` (added)
