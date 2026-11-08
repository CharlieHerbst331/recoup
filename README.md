# recoup
Recoup: AI agents for AR deductions, disputes, and insured-receivable claims (Ramp x BBS hackathon)

Step **006-1 / F0 is complete**, accepted by the owner on 2026-11-08 after implementation,
offline verification and merge to `main`. This delivers contracts v1, pure citation
resolution and contract testing stubs. Owner acceptance closes the review gate;
independent Reviewer/Verifier reviews were not performed. See the
[acceptance record](progress/charles/006-1-ACCEPTANCE.md).

The bundled design documents retain their original proposal labels as historical
source text. Current milestone status is recorded above and in [docs/INDEX.md](docs/INDEX.md).

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
