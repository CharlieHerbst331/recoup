# Recoup UI

## Run the UI

The primary workbench uses **React + shadcn/ui**, backed by the existing Python
service. From the repository root:

```sh
npm --prefix recoup/ui/frontend ci
npm --prefix recoup/ui/frontend run build
RECOUP_LLM=fake .venv/bin/python -m recoup.ui.server --port 8501 --db runs/your-demo.db
```

Open `http://127.0.0.1:8501`. The server binds to localhost only. Dashboard shows
all loaded cases with searchable filters, current approval tags, MOCK submission
tags, and checklist or review gaps. Counts are case counts, while case tags show
the number of drafts or receipts. On a narrow screen, use **Toggle navigation**
to open the case list and **Simulation lab**.

## Two-minute demo

The main view is one case list with a **Continue review** action. Each case shows
one recommendation and the current approval/submission button. The single **Demo**
label in the header identifies the synthetic data, MOCK actions, and LLM mode via
its tooltip; the stored documents, drafts, approvals, and receipts retain provenance.

Follow Harbor's valid credit, Northwind's invalid deduction, and Juniper's valid
credit plus unpaid debt through the existing service workflow. Use **Advance to
next event** when prompted. A missing statement prevents claim submission until
it arrives. The final case list distinguishes a posted credit, buyer repayment,
and a claim awaiting insurer review; the remaining claim balance stays open.

**View draft & supporting documents** reveals the exact saved draft, recipient,
allocations, sources, and versions. **Details** contains documents, agent activity,
policy checks, audit, and assessment. These are optional for the short recording.
The navigation menu holds **Demo controls** for manual time, agent runs, and saved
runs; **Run settings → Start fresh demo** preserves earlier databases.

[DEMO_SCRIPT.md](DEMO_SCRIPT.md) is the two-minute recording path. Existing policy,
readiness, approval, and financial behavior follows design/02 §4–§6. This UI step
changes presentation only; source data and the offline agent behavior are unchanged.

## Components and development

`frontend/src/components/ui` contains the actual components installed from the
[official shadcn registry](https://ui.shadcn.com/docs/installation/vite), plus its
MIT license and shared styles. Product screens compose these primitives; theme
tokens live in `frontend/src/index.css`. Ramp is not included.

Contract models, gates, money calculations, and action execution remain in the
Python service. `api.py` supplies presentation data, formats USD in Python, and
transports cents as strings so browser editing preserves exact integer values.
`server.py` serves the build and dispatches JSON requests to the facade. No new
Python dependencies are required. The npm lockfile pins the frontend toolchain.

For development, run the Python server on port 8503 and
`npm --prefix recoup/ui/frontend run dev` in another terminal. Vite proxies API
requests to that local backend. Build with `npm --prefix recoup/ui/frontend run
build`; run backend checks with `make check`. API tests use app-built in-memory
Worlds and no network.

The earlier Streamlit UI remains available with
`RECOUP_LLM=fake .venv/bin/python -m streamlit run recoup/ui/streamlit_app.py`.
