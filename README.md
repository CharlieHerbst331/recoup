# Recoup

Recoup is a single-user accounts receivable workbench for investigating short-paid
and unpaid invoices. A reviewer can trace a deduction to its evidence, inspect a
recommended credit, dispute, information request, or insurance step, and decide
whether to approve the proposed action.

**The React workbench is the demo and the primary interface.** Its Python agent
uses tools to investigate evidence and draft actions. The rules engine computes
amounts and the service checks proposed actions before they can be submitted.
The demo uses **SYNTHETIC** records, **MOCK** submissions, and **LLM: fake** by
default. It needs no API key and does not contact buyers or insurers.

## Run the demo

From the repository root, with Python 3.11 and Node.js 22.12 or newer:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
npm --prefix recoup/ui/frontend ci
npm --prefix recoup/ui/frontend run build
RECOUP_LLM=fake .venv/bin/python -m recoup.ui.server --port 8501 --db runs/reviewer.db
```

Open <http://127.0.0.1:8501>. Click **Load cases**, then **Continue review**.
Open **View draft & supporting documents** to trace an action to its source.
**Approve** and **Submit** are separate steps. Follow **Advance to next event**
to release new evidence on the simulated clock.

| Case | What to verify |
| --- | --- |
| **Harbor Market** | A signed price amendment supports a $500 credit. The MOCK credit closes the open balance. |
| **Northwind Grocers** | The signed receiving record supports a $3,120 shortage dispute. A later synthetic bank confirmation closes the balance; the dispute receipt itself does not post a payment. |
| **Juniper Provisions** | After a $2,150 credit, $5,000 remains unpaid. A missing statement blocks the claim. When the statement arrives, the refreshed package needs a new approval. The MOCK claim leaves $5,000 open. |

See the [recording walkthrough](recoup/ui/DEMO_SCRIPT.md) for exact clicks and
the [UI guide](recoup/ui/README.md) for resetting the demo or enabling a live
provider. The [CLI](recoup/cli.py) and [earlier Streamlit UI](recoup/ui/README.md#components-and-development)
use the same service.

## Where to verify the implementation

Start at the [React HTTP server](recoup/ui/server.py) and its [JSON adapter](recoup/ui/api.py),
then follow the calls through [`recoup.app.build`](recoup/app.py). The
[technical design](docs/design/02-technical-design.md) is the behavior contract.

| Check | Implementation | Executable evidence |
| --- | --- | --- |
| The agent investigates and drafts; rules supply the amounts and citations for deduction findings (§5.1–5.4). | [Harness](recoup/engine/harness.py), [tools](recoup/engine/tools.py), [rules](recoup/engine/rules.py) | [Engine acceptance](tests/app/test_engine_acceptance.py), [rule tests](tests/engine/test_rules.py) |
| A proposal needs a matching approval, and changed evidence or missing documents can block submission (§4.2–4.3, §5.5–5.6). | [SQLite world](recoup/world/store.py), [gates](recoup/engine/gates.py), [readiness](recoup/engine/readiness.py) | [Action tests](tests/world/test_actions.py), [full demo through the service](tests/ui/test_reviewer_demo.py) |
| Intake and ledger changes can be checked independently of the UI (§3.6, §3.9). | [Remittance](recoup/world/remittance.py), [ledger](recoup/world/ledger.py) | [Remittance tests](tests/world/test_remittance.py), [fully paid cases](tests/app/test_paid_demo.py), [CLI financial examples](cases/ambition/README.md) |
| The provider is replaceable; live transport and error handling can be tested offline (§5.9). | [Provider factory](recoup/engine/factory.py), [live adapter](recoup/engine/llm/openai_compat.py), [replay adapter](recoup/engine/llm/replay.py) | [Live adapter tests](tests/engine/test_openai_compat.py), [failure tests](tests/engine/test_live_failures.py) |

```sh
make check
RECOUP_LLM=fake .venv/bin/recoup --db :memory: check-regression
```

`make check` runs Ruff and the offline Python test suite. For a focused review,
run `.venv/bin/python -m pytest -q tests/ui/test_reviewer_demo.py tests/world/test_actions.py`.
The guided React fixtures live in [`recoup/ui/demo`](recoup/ui/demo); the CLI
regression fixtures and paid examples are separate under [`cases/demo`](cases/demo).

## What the evidence supports

The guided order and evidence releases are scripted for the demo. The offline
agent still exercises the service, including approval checks, event processing,
receipts, and ledger changes. **Company Data** is an illustrative connector
catalog. Real integrations, collections, and insurer decisions are outside the demo.

The [Alder live-model evaluation](progress/sonny/unseen-alder-2718/EVALUATION.md)
is a separate, single synthetic case with saved drafts and traces from an earlier
deployed snapshot. It records usable proposals as well as a loop escalation,
a stale human-review status, and a recording conflict on a repeat attempt.
The offline suite validates this checkout; the live record does not establish
general model reliability or production readiness.

See the [documentation index](docs/INDEX.md) for specifications and historical
handoffs.
