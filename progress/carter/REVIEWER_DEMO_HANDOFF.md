# Reviewer demo — current task scope

Current step: add fictional buyer marks and action type colors to the React
workbench, plus a read-only mock Company Data catalog in both LLM modes. As
requested, the catalog uses "Connected" for every source. Keep the saved demo,
approval behavior, and provider controls intact.

Implementation scope for this task:
- `recoup/ui/**`, `tests/ui/**`, `progress/carter/**`

This step edits only UI, UI tests, and progress documentation. Use local artwork
and static connector examples. No new dependencies, integrations, or provider calls.
Existing rules, gates, financial calculations,
contracts, core fixtures, and provider interfaces stay in place. Reviewer bundles live under
`recoup/ui/demo/`; original `cases/demo/**` and regression fixtures are preserved.
Normative behavior: design/02 §4.2–4.5, §5.3–5.9, §6.

The prior branding and model switch handoff is recorded in
[BRAND_LIVE_ACCEPTANCE.md](BRAND_LIVE_ACCEPTANCE.md).

The updated preview is at http://127.0.0.1:8503/#sources with a separate day-zero
demo. Browser QA covered the case list, a dispute recommendation, all 12 source
cards, keyboard and sidebar navigation, Back/Forward, and reload. Checked the
layout at 1440 × 1000 and 390 × 844. The earlier saved run was preserved.
The catalog stayed open across both directions of the LLM mode switch and on a
live-mode reload. That walkthrough used an isolated server with a placeholder
key and a local-only provider address; no model call was made.
Production frontend build passed. Final `make check`: Ruff lint and format,
1,156 tests passed, 2 skipped. Log: `runs/recoup-company-data-verified-check.log`.

Changed files:

- `recoup/ui/README.md`
- `recoup/ui/api.py`
- `recoup/ui/frontend/src/App.jsx`
- `recoup/ui/frontend/src/components/audit-trail.jsx`
- `recoup/ui/frontend/src/components/case-labels.jsx`
- `recoup/ui/frontend/src/components/case-page.jsx`
- `recoup/ui/frontend/src/components/company-data.jsx`
- `recoup/ui/frontend/src/components/dashboard.jsx`
- `recoup/ui/frontend/src/components/workbench-sidebar.jsx`
- `recoup/ui/frontend/src/lib/ui.jsx`
- `tests/ui/test_react_api.py`
- `tests/ui/test_reviewer_demo.py`
- `progress/carter/REVIEWER_DEMO_HANDOFF.md`
- `progress/carter/PROGRESS.md`
