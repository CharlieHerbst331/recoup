# Ramp palette and repository handoff

This step applies the earlier Ramp-inspired lime, charcoal, and warm-neutral colors
while preserving the simplified layout and demo behavior. Only theme tokens and
progress documentation changed in this step. No dependencies were added.

Palette: primary lime `#e4f222`, charcoal `#191919`, warm background `#f7f7f2`,
white surfaces, neutral borders `#e4e4df`, and muted text `#62625c`. The reference
is the earlier Ramp-inspired styling in repository commit `8c4088c`.

## Validation

- Frontend production build passed.
- `make check`: **1153 passed, 2 skipped**, 395.42 seconds; Ruff lint/format passed.
- Browser verified the palette on the existing claim screen. The current demo run
  and layout were preserved. The earlier complete short-flow check took 49 seconds.
- Screenshot: `runs/ramp-palette.png`. Check log: `runs/ramp-palette-check.log`.
- `git diff --cached --check` passed.

No remaining app blockers were encountered. Normative behavior stays in design/02 §4–§6.

## Files edited in this step

- `recoup/ui/frontend/src/index.css`
- `progress/carter/REVIEWER_DEMO_HANDOFF.md`
- `progress/carter/REVIEWER_DEMO_ACCEPTANCE.md`
- `progress/carter/PROGRESS.md`

## Publication

The authorized publication target is the existing `codex/enterprise-ui` branch in
`CharlieHerbst331/recoup`. The commit includes the complete pending UI/demo work
from this conversation, including the earlier React migration, three-case
simulation, policy/claim demonstration, simplified presentation, and tests.
Unrelated pre-existing `arhcive/` and `recoup-006-charles-bundle-r10.md` are excluded.
Dependencies, builds, local databases, screenshots, and check logs remain ignored.

The complete commit file manifest follows:

- `progress/carter/PROGRESS.md`
- `progress/carter/REVIEWER_DEMO_ACCEPTANCE.md`
- `progress/carter/REVIEWER_DEMO_HANDOFF.md`
- `progress/carter/UI_HANDOFF.md`
- `recoup/engine/demo_copy.py`
- `recoup/engine/harness.py`
- `recoup/engine/llm/fake.py`
- `recoup/engine/scheduler.py`
- `recoup/engine/tools.py`
- `recoup/ui/DEMO_SCRIPT.md`
- `recoup/ui/README.md`
- `recoup/ui/api.py`
- `recoup/ui/dashboard.py`
- `recoup/ui/demo/C/bundle.json`
- `recoup/ui/demo/H/bundle.json`
- `recoup/ui/demo/N/bundle.json`
- `recoup/ui/frontend/.gitignore`
- `recoup/ui/frontend/components.json`
- `recoup/ui/frontend/index.html`
- `recoup/ui/frontend/jsconfig.json`
- `recoup/ui/frontend/package-lock.json`
- `recoup/ui/frontend/package.json`
- `recoup/ui/frontend/src/App.jsx`
- `recoup/ui/frontend/src/components/action-panel.jsx`
- `recoup/ui/frontend/src/components/agent-activity.jsx`
- `recoup/ui/frontend/src/components/audit-trail.jsx`
- `recoup/ui/frontend/src/components/case-page.jsx`
- `recoup/ui/frontend/src/components/dashboard.jsx`
- `recoup/ui/frontend/src/components/documents.jsx`
- `recoup/ui/frontend/src/components/insurance-review.jsx`
- `recoup/ui/frontend/src/components/reviewer-journey.jsx`
- `recoup/ui/frontend/src/components/ui/LICENSE.md`
- `recoup/ui/frontend/src/components/ui/accordion.jsx`
- `recoup/ui/frontend/src/components/ui/alert.jsx`
- `recoup/ui/frontend/src/components/ui/badge.jsx`
- `recoup/ui/frontend/src/components/ui/button.jsx`
- `recoup/ui/frontend/src/components/ui/card.jsx`
- `recoup/ui/frontend/src/components/ui/dialog.jsx`
- `recoup/ui/frontend/src/components/ui/input.jsx`
- `recoup/ui/frontend/src/components/ui/select.jsx`
- `recoup/ui/frontend/src/components/ui/separator.jsx`
- `recoup/ui/frontend/src/components/ui/shadcn.css`
- `recoup/ui/frontend/src/components/ui/sheet.jsx`
- `recoup/ui/frontend/src/components/ui/sidebar.jsx`
- `recoup/ui/frontend/src/components/ui/skeleton.jsx`
- `recoup/ui/frontend/src/components/ui/table.jsx`
- `recoup/ui/frontend/src/components/ui/tabs.jsx`
- `recoup/ui/frontend/src/components/ui/textarea.jsx`
- `recoup/ui/frontend/src/components/ui/tooltip.jsx`
- `recoup/ui/frontend/src/components/workbench-sidebar.jsx`
- `recoup/ui/frontend/src/hooks/use-mobile.js`
- `recoup/ui/frontend/src/index.css`
- `recoup/ui/frontend/src/lib/ui.jsx`
- `recoup/ui/frontend/src/main.jsx`
- `recoup/ui/frontend/vite.config.js`
- `recoup/ui/reviewer.py`
- `recoup/ui/server.py`
- `recoup/ui/streamlit_app.py`
- `tests/engine/test_demo_copy.py`
- `tests/ui/test_dashboard.py`
- `tests/ui/test_demo_controls.py`
- `tests/ui/test_react_api.py`
- `tests/ui/test_reviewer_demo.py`
- `tests/ui/test_streamlit_app.py`
