# Paid SYNTHETIC demo cases — task handoff

Authorized by the user's 2026-11-10 request; one implementation step, offline only.
Normative sources: docs/design/02 §3.7, §4.5 and §5.3–5.9.

Exact edit allowlist (including this task-handoff bootstrap):
- progress/sonny/PAID-DEMO-HANDOFF.md
- progress/sonny/PROGRESS.md (append done / next / question only)
- cases/demo/PAID-FULL/bundle.json
- cases/demo/PAID-INSTALLMENTS/bundle.json
- recoup/ui/workbench.py
- tests/app/test_paid_demo.py
- tests/ui/test_workbench.py
- tests/world/test_fixtures.py
- README.md

Add exactly two distinct fully paid fixtures and load them beside H/C/N through
app.build → intake → rules → agent. Verify SQLite in memory with FakeLLM,
empty deductions/findings/proposals/actions, preserved H/C/N results and replay
idempotency. Extend the existing demo UI acceptance and fixture inventory checks.
No contracts, app composition, financial rules, agent, dependencies or other files
may be edited. No live provider, real send, deployment or subsequent step.
Run make check, list changed files, append the three progress lines, then stop.
