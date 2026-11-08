# recoup
Recoup: AI agents for AR deductions, disputes, and insured-receivable claims (Ramp x BBS hackathon)

Step 006-1 implements **PROPOSED v1** contracts, pure citation resolution and contract
testing stubs. The design review and F0 freeze are pending. See [docs/INDEX.md](docs/INDEX.md)
and [technical design §3 and §8.1](docs/design/02-technical-design.md).

Use Python 3.11:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
make check
```

Direct dependencies and extras are pinned to the installed versions in `pyproject.toml`.
Tests run offline without an API key; `make check` selects `RECOUP_LLM=fake`.
The optional `.[ocr]` extra is declared for later ingestion work.

The configured `recoup` CLI entrypoint belongs to a later step and cannot run yet.
World, engine, UI, benchmarks and app wiring are also later steps.
