# recoup/ui/AGENTS.md and recoup/bench/AGENTS.md (owned by Carter)
- UI uses recoup.app.build(). It reads world.list_cases, view, history and list_quarantined. It writes only through Recoup methods (run, advance, add_evidence, confirm_field, edit, approve, reject, submit). Put logic in pure helper functions with tests.
- Show the "DEMO CLOCK" banner and the "MOCK ACKNOWLEDGMENT — not sent to any real system" label. The money table never shows a total, and cash collected is always $0.
- Bench imports recoup.contracts and recoup.app only (docs/design/02 §2). Tools come from `Recoup.tool_session`; baselines are injected with `build(config, controller=...)` (§4.5, §8.3).
- Bench: the runtime never sees the oracle path. Scan for sentinels. The denominator is N_planned, and an incomplete arm prints NOT EVALUATED. Unknown price fails closed. Offline means "offline", never "free".
- Track T compares T-min against H-M using the same tools, model, events and budgets. Never score a tool-less chat on Track T.
- Never open bench/holdout oracles before scoring. Commit the T-min prompt before any harness tuning. Spend nothing without an approved budget in PLAN.lock.

