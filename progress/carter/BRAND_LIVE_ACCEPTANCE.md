# Supplied branding and live model switch

The supplied Recoup wordmark and Ramp symbol are integrated into the existing
workbench. The sticky header collapses to the symbol on scroll, with reduced
motion support. The current dashboard, cases, and simulation day are preserved.

**Toggle navigation → Demo controls → Real LLM** switches future runs between
the offline agent and the configured provider, using the same synthetic data.
The server reads `OPENAI_API_KEY` and `RECOUP_MODEL`; switching makes no model
request and does not relabel saved activity. Business actions remain MOCK.
Behavior follows design/02 §5.9 and §6.

- Browser verified the expanded and collapsed logo, navigation, and the switch's
  setup state. Screenshots: `runs/recoup-wordmark.jpg`,
  `runs/recoup-collapsed-mark.jpg`, and `runs/recoup-model-controls.jpg`.
- Production build passed. The focused model tests use the contract's scripted
  responses to verify mode switching, simulation progress, and MOCK receipts.
- `make check` passed: Ruff lint and format, 1,156 tests passed, 2 skipped.
  Full output: `runs/recoup-brand-live-check.log`.
- No live request was sent. A server key and model are needed to try live runs.

## Changed files

- `progress/carter/BRAND_LIVE_ACCEPTANCE.md`
- `progress/carter/PROGRESS.md`
- `progress/carter/REVIEWER_DEMO_HANDOFF.md`
- `recoup/ui/README.md`
- `recoup/ui/api.py`
- `recoup/ui/frontend/public/brand/README.md`
- `recoup/ui/frontend/public/brand/ramp-base.svg`
- `recoup/ui/frontend/public/brand/ramp-curve.svg`
- `recoup/ui/frontend/public/brand/ramp-logo.svg`
- `recoup/ui/frontend/src/App.jsx`
- `recoup/ui/frontend/src/components/brand/brand-paths.js`
- `recoup/ui/frontend/src/components/brand/scroll-brand.css`
- `recoup/ui/frontend/src/components/brand/scroll-brand.jsx`
- `recoup/ui/frontend/src/components/ui/switch.jsx`
- `recoup/ui/frontend/src/components/workbench-sidebar.jsx`
- `recoup/ui/provider.py`
- `recoup/ui/server.py`
- `tests/ui/test_react_api.py`
