# Reviewer demo — current task scope

Current step: incorporate the user-supplied logo/scroll design into the concise
workbench, and expose a key-gated real-LLM toggle with the existing synthetic
simulation backend. Keep credentials server-side, mode changes free of model
calls, and all outgoing actions MOCK with the existing approval gates.

Implementation scope for this task:
- `recoup/ui/**`, `tests/ui/**`, `progress/carter/**`

This step edits only UI, UI tests, and progress documentation. Source design files
under Downloads remain unchanged. Reuse the existing live adapter and supplied
React/SVG assets; no new dependencies or provider calls in tests.
Existing rules, gates, financial calculations,
contracts, core fixtures, and provider interfaces stay in place. Reviewer bundles live under
`recoup/ui/demo/`; original `cases/demo/**` and regression fixtures are preserved.
Normative behavior: design/02 §4.2–4.5, §5.3–5.9, §6.
