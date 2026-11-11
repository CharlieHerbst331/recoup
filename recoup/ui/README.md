# Recoup UI

## Run the UI

The primary workbench uses **React + shadcn/ui**, backed by the existing Python
service. From the repository root:

```sh
npm --prefix recoup/ui/frontend ci
npm --prefix recoup/ui/frontend run build
RECOUP_LLM=fake .venv/bin/python -m recoup.ui.server --port 8501 --db runs/your-demo.db
```

Open `http://127.0.0.1:8501`. The server binds to localhost only. Use the case
list to review work and **Toggle navigation → Demo controls** to run the simulation.

**Company Data** shows the workspace's mock source catalog, including shared
documents, conversations, finance systems, databases, and external portals.
It describes the records each source could contribute and stays available in
both LLM modes. The displayed connections do not link accounts or fetch data.

## Use a real model with the demo

The demo starts with the offline agent. To enable **Real LLM** in **Demo controls**,
set `OPENAI_API_KEY` and `RECOUP_MODEL` in the Python server's environment, then
restart it with the command above. To resume a saved run, pass the database path
shown in **Run settings** to `--db`. Use a model your key can access that supports
tool calls. Keep the key on the server
([OpenAI authentication docs](https://developers.openai.com/api/reference/overview)).

Switching modes keeps your database, simulation day, approvals, and receipts and
makes no model request. The next agent run uses the selected mode, including runs
triggered by loading cases or advancing time. Live mode sends synthetic case
context to the configured model provider and may incur usage charges. Business
actions are still MOCK and require the existing approvals. Without server
configuration, the switch is disabled and shows what to set. The switch is for
the current server session; start in `RECOUP_LLM=fake` for the recorded walkthrough.

## Two-minute demo

The main view is one case list with a **Continue review** action. Fictional
customer marks identify the demo buyers, and color and text distinguish the
recommended action types. Each case shows one recommendation and the current
approval/submission button. The single **Demo**
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
readiness, approval, and financial behavior follows design/02 §4–§6.

## Components and development

`frontend/src/components/ui` contains the actual components installed from the
[official shadcn registry](https://ui.shadcn.com/docs/installation/vite), plus its
MIT license and shared styles. Product screens compose these primitives; theme
tokens live in `frontend/src/index.css`. The supplied Recoup lockup and Ramp
symbol are used in the header, with a scroll reveal that respects reduced motion.
The [reference artwork](frontend/public/brand/README.md) is retained with its provenance.

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
