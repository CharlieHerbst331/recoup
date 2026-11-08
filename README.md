# recoup

Recoup is a single-user AR case workbench. Data is **SYNTHETIC**, actions are
**MOCK**, and the default LLM mode is **fake**. No real sends or cash collection
are implemented.

Charles's 006-2B/3/4 work provides the SQLite World, persisted evidence and fact
history, approval-bound mock transactions, event release, and policy/demo/regression
fixtures. 006-5 provides CLI and factory-selection plumbing. The actual Sonny
engine/validator/scheduler/factory is absent from this checkout: the CLI labels
its contract-stub runtime explicitly. Regression verdict acceptance and the full
H demo remain blocked on that provider. Contract review/F0 freeze remains pending.
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
.venv/bin/recoup init
.venv/bin/recoup load cases/demo/H cases/demo/C cases/demo/N
.venv/bin/recoup status H
.venv/bin/recoup advance --to-next-due
.venv/bin/recoup history H
.venv/bin/recoup check-regression
```

The default database is `runs/recoup.db`; set `RECOUP_DB` to use another path.
`check-regression` evaluates each case in an isolated in-memory database, leaving
that working database unchanged, and exits nonzero on a mismatch. With contract
stubs it correctly fails the seven USD engine cases; EUR quarantine passes.

When Sonny's engine package is installed, `build` selects its documented factory
inside the composition root. Provider import/initialization errors propagate.
A supplied controller replaces the harness and prevents harness LLM construction.
No live API budget, merge, push, tag, or external send is authorized by this work.
