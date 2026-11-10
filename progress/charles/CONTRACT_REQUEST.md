# 006-2A: selected-case run routing — resolved 2026-11-09 PT

Resolved in the additive shared-contract candidate: design/02 §3.5 defines
`ScopedController.scope(case_ids)` and §4.5 defines its use. The default app
composition adapter supplies it without changing `Controller.react` or custom
controller identity. Unsupported custom controllers reject selected-case runs
before callback. `tests/app/test_scoped_controller.py` proves two-case isolation,
pending-event preservation, rollback, scope restoration and normal all-case runs.
Publication and candidate pin are in SONNY-UNBLOCK-ACCEPTANCE.md. The original
request below is retained as history.

Candidate: `89675c0b6ac676fa28c3475f58134689b74c274c`. No contract files changed.

Design/02 §4.5 specifies `Recoup.run(case_id)` and a single
`controller.react(world, [], run_id)` for the selected case(s). The actual
`Controller.react` port (§3.5) takes only World, events and run_id. It cannot
receive the selected case when events must be empty and the injected World is
unchanged. Calling engine.investigate directly would violate §4.5 isolation.

Consumer evidence: `tests/app/test_facade_unit.py::test_run_returns_views_after_callback_and_checks_unknown_case`
proves returned-view selection; `test_public_mutations_dispatch_only_to_selected_controller`
proves the specified empty-event callback to the supplied controller. Neither
can prove that an actual controller investigates only the requested case.

Minimum requested resolution before actual harness integration: Charles and
the controller owner should clarify the selected-case channel in §3.5/§4.5;
if case targeting is required at this boundary, approve the smallest shared
signature adjustment in a separately pinned/reviewed contract update. Do not
encode a case id into run_id or fabricate DomainEvents to work around the port.

Current facade follows the existing signature, returns the requested views,
and never calls investigate/handle. A two-case real-controller test verifying
that `run(A)` does not investigate B remains BLOCKED on this resolution and
the actual engine provider. Other facade unit work is unaffected.
