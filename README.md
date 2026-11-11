# Recoup

Recoup helps a finance specialist review unpaid and short-paid invoices. Open a
case, inspect the supporting documents, and review proposed disputes, credits,
information requests, and follow-ups in one workbench.

Recoup provides a local React workbench and a Streamlit workbench, backed by SQLite. Demo data is
**SYNTHETIC**, actions are **MOCK**, and the default **LLM: fake** mode works
without an API key. No real messages are sent or cash collected.

## Run the app

Use Python 3.11. See the [React workbench instructions](recoup/ui/README.md)
for the case navigator and Company Data page. To run the local Streamlit demo
from the repository root:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
RECOUP_LLM=fake .venv/bin/python -m streamlit run recoup/ui/streamlit_app.py
```

Open the local URL printed by Streamlit. For a fresh walkthrough, set
**Database path** in the sidebar to an unused path such as `runs/ui-demo.db`,
then click **Load demo cases H, C and N**.

1. Open **H** to review Northwind Grocers' shortage and promotion deductions.
2. Inspect a proposed action. Use **Edit proposal** to revise its draft, then
   **Approve** and **Submit** separately to create a MOCK receipt.
3. Click **Advance to next due** to move the simulated clock and see new
   documents, revised proposals, and updated checklists.

## What is implemented

- A case queue with balances, deadlines, and a separate list of rejected imports.
- Case details with document versions, cited deduction decisions, action review,
  insurance document checklists, and an activity history.
- Simulated events and follow-ups, plus a CLI for case intake and review.
- CLI examples for multi-invoice payment allocation and counteroffers in
  [financial examples](cases/ambition/README.md).

The [hosted Streamlit workbench](progress/carter/SHARED-BACKEND-HANDOFF.md) uses
a shared access secret. The React Company Data catalog illustrates potential
integrations. Live-model and OCR verification are separate from offline tests;
`doctor` reports local capabilities.

## Development

```sh
make check
.venv/bin/recoup doctor
.venv/bin/recoup --db :memory: check-regression
.venv/bin/recoup --help
```

Use `.venv/bin/recoup --db runs/demo.db load cases/demo` to import the core
demo cases and both fully paid synthetic cases through the CLI.

The CLI defaults to `runs/recoup.db`; override it with `--db` or `RECOUP_DB`.
The UI uses its sidebar database path, initially `runs/demo.db`.

See [UI instructions](recoup/ui/README.md) for demo controls and
[the documentation index](docs/INDEX.md) for designs, ownership, and verification
records. The technical specification is [design/02](docs/design/02-technical-design.md)
(§6 UI; §7 CLI).
