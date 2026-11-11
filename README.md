# recoup

Recoup is a single-user AR case workbench. Data is **SYNTHETIC**, actions are
**MOCK**, and the default LLM mode is **fake**. No real sends or cash collection
are implemented.

This branch includes Charles's SQLite World, approval-bound mock transactions,
evidence history, fixtures, app and CLI, together with Sonny's actual engine,
financial gates, scheduler, counteroffers and offline FakeLLM. Multi-invoice
historical remittances load through the shared World/app/CLI. The default runtime
uses those installed providers; it requires no model key.

006-1 / F0 was accepted by the owner on 2026-11-08. The owner-acceptance
record is preserved in [006-1 acceptance](progress/charles/006-1-ACCEPTANCE.md);
independent Reviewer/Verifier reviews were not performed. The integrated
implementation is merged into `main` at the owner's request; see the
[merge record](progress/charles/006-MAIN-MERGE-ACCEPTANCE.md).

The final branch integration checks and remaining limitations are recorded in
[Charles's final acceptance](progress/charles/006-FINAL-INTEGRATION-ACCEPTANCE.md).
Test verification does not imply independent review or a `contract-v1` tag.
Carter's UI and benchmark implementation are separate work.
See [docs/INDEX.md](docs/INDEX.md), [design/02](docs/design/02-technical-design.md),
and [progress/charles/PROGRESS.md](progress/charles/PROGRESS.md).

Use Python 3.11:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
make check
```

Dependencies are pinned in `pyproject.toml`; no API key is needed for offline
checks. The optional `.[ocr]` extra is declared; `doctor` reports availability,
and an available dependency alone does not prove ingestion works.

```sh
.venv/bin/recoup doctor
.venv/bin/recoup --db runs/demo.db init
.venv/bin/recoup --db runs/demo.db load cases/demo
.venv/bin/recoup --db runs/demo.db status H
.venv/bin/recoup --db runs/demo.db advance --to-next-due
.venv/bin/recoup --db runs/demo.db history H
.venv/bin/recoup --db :memory: check-regression
.venv/bin/recoup --db runs/remittance-demo.db load-remittance cases/ambition/multi-invoice/remittance.json
.venv/bin/recoup --db runs/offer-demo.db load cases/ambition/counteroffer
```

The default database is `runs/recoup.db`; set `RECOUP_DB` to use another path.
`check-regression` evaluates each case in an isolated in-memory database, leaving
that working database unchanged, and exits nonzero on a mismatch. All eight
published cases pass with the actual offline engine, including EUR quarantine.
Use a fresh demo database when starting a demonstration from day zero.

Inspect generated proposal IDs and versions with `status CASE`. Use `edit`,
`approve` and `submit` to review and execute a mock action; approval applies only
to that exact version. See `recoup COMMAND --help` and design/02 §7. The app never
automatically approves proposals. Counteroffer and remittance examples are
documented in [cases/ambition](cases/ambition/README.md).

When Sonny's engine package is installed, `build` selects its documented factory
inside the composition root. Provider import/initialization errors propagate.
A supplied controller replaces the harness and prevents harness LLM construction.
Real OCR and live-model proof are separate from the offline tests. Missing
optional capabilities appear in `doctor`; a detected prerequisite alone does
not establish extraction accuracy. Legacy uncited fact revisions require an
explicit migration rather than silently repairing historical evidence.
