# UI handoff

The primary UI is React + shadcn/ui at http://127.0.0.1:8501. The Python facade,
contracts, engine, and World were not changed. Ramp is not included.

Dashboard provides case-level counts, approval and MOCK submission tags, search,
filters, and direct case navigation. Simulation controls and a guided demo are
visible. Fresh runs preserve earlier databases. The Streamlit UI remains available.

Validation: make check passed (1146 passed, 2 skipped); Vite production build
passed; npm dependency audit is clear. Browser checks covered the desktop table,
narrow-screen cards and sidebar, edit/approve/submit, a MOCK receipt, next-due day 3,
revised POD, correction proposals, and readiness. No app blockers remain.

Run instructions: [recoup/ui/README.md](/Users/charlieherbst/recoup/recoup/ui/README.md).
Preview artifact: [dashboard screenshot](/Users/charlieherbst/recoup/runs/react-dashboard.png).
Runtime simulation databases and screenshot artifacts are ignored under runs/.

## Changed files

- [progress/carter/PROGRESS.md](/Users/charlieherbst/recoup/progress/carter/PROGRESS.md)
- [progress/carter/UI_HANDOFF.md](/Users/charlieherbst/recoup/progress/carter/UI_HANDOFF.md)
- [recoup/ui/README.md](/Users/charlieherbst/recoup/recoup/ui/README.md)
- [recoup/ui/api.py](/Users/charlieherbst/recoup/recoup/ui/api.py)
- [recoup/ui/dashboard.py](/Users/charlieherbst/recoup/recoup/ui/dashboard.py)
- [recoup/ui/frontend/.gitignore](/Users/charlieherbst/recoup/recoup/ui/frontend/.gitignore)
- [recoup/ui/frontend/components.json](/Users/charlieherbst/recoup/recoup/ui/frontend/components.json)
- [recoup/ui/frontend/index.html](/Users/charlieherbst/recoup/recoup/ui/frontend/index.html)
- [recoup/ui/frontend/jsconfig.json](/Users/charlieherbst/recoup/recoup/ui/frontend/jsconfig.json)
- [recoup/ui/frontend/package-lock.json](/Users/charlieherbst/recoup/recoup/ui/frontend/package-lock.json)
- [recoup/ui/frontend/package.json](/Users/charlieherbst/recoup/recoup/ui/frontend/package.json)
- [recoup/ui/frontend/src/App.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/App.jsx)
- [recoup/ui/frontend/src/components/action-panel.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/action-panel.jsx)
- [recoup/ui/frontend/src/components/case-page.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/case-page.jsx)
- [recoup/ui/frontend/src/components/dashboard.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/dashboard.jsx)
- [recoup/ui/frontend/src/components/documents.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/documents.jsx)
- [recoup/ui/frontend/src/components/ui/LICENSE.md](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/LICENSE.md)
- [recoup/ui/frontend/src/components/ui/accordion.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/accordion.jsx)
- [recoup/ui/frontend/src/components/ui/alert.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/alert.jsx)
- [recoup/ui/frontend/src/components/ui/badge.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/badge.jsx)
- [recoup/ui/frontend/src/components/ui/button.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/button.jsx)
- [recoup/ui/frontend/src/components/ui/card.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/card.jsx)
- [recoup/ui/frontend/src/components/ui/dialog.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/dialog.jsx)
- [recoup/ui/frontend/src/components/ui/input.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/input.jsx)
- [recoup/ui/frontend/src/components/ui/select.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/select.jsx)
- [recoup/ui/frontend/src/components/ui/separator.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/separator.jsx)
- [recoup/ui/frontend/src/components/ui/shadcn.css](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/shadcn.css)
- [recoup/ui/frontend/src/components/ui/sheet.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/sheet.jsx)
- [recoup/ui/frontend/src/components/ui/sidebar.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/sidebar.jsx)
- [recoup/ui/frontend/src/components/ui/skeleton.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/skeleton.jsx)
- [recoup/ui/frontend/src/components/ui/table.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/table.jsx)
- [recoup/ui/frontend/src/components/ui/tabs.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/tabs.jsx)
- [recoup/ui/frontend/src/components/ui/textarea.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/textarea.jsx)
- [recoup/ui/frontend/src/components/ui/tooltip.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/ui/tooltip.jsx)
- [recoup/ui/frontend/src/components/workbench-sidebar.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/components/workbench-sidebar.jsx)
- [recoup/ui/frontend/src/hooks/use-mobile.js](/Users/charlieherbst/recoup/recoup/ui/frontend/src/hooks/use-mobile.js)
- [recoup/ui/frontend/src/index.css](/Users/charlieherbst/recoup/recoup/ui/frontend/src/index.css)
- [recoup/ui/frontend/src/lib/ui.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/lib/ui.jsx)
- [recoup/ui/frontend/src/main.jsx](/Users/charlieherbst/recoup/recoup/ui/frontend/src/main.jsx)
- [recoup/ui/frontend/vite.config.js](/Users/charlieherbst/recoup/recoup/ui/frontend/vite.config.js)
- [recoup/ui/server.py](/Users/charlieherbst/recoup/recoup/ui/server.py)
- [recoup/ui/streamlit_app.py](/Users/charlieherbst/recoup/recoup/ui/streamlit_app.py)
- [tests/ui/test_dashboard.py](/Users/charlieherbst/recoup/tests/ui/test_dashboard.py)
- [tests/ui/test_demo_controls.py](/Users/charlieherbst/recoup/tests/ui/test_demo_controls.py)
- [tests/ui/test_react_api.py](/Users/charlieherbst/recoup/tests/ui/test_react_api.py)
- [tests/ui/test_streamlit_app.py](/Users/charlieherbst/recoup/tests/ui/test_streamlit_app.py)
