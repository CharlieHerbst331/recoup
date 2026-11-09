"""Command-line workbench via the facade (design/02 §7 and §4.5)."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from enum import Enum
from functools import wraps
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import BundleDoc
from recoup.contracts.capabilities import scan_capabilities
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.models import LineAmount
from recoup.contracts.money import Money

app = typer.Typer(no_args_is_help=True, help="SYNTHETIC AR workbench; all actions are MOCK.")


def _handled(function):
    @wraps(function)
    def invoke(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except GateError as exc:
            for issue in exc.issues:
                suffix = f" [{issue.line_id}]" if issue.line_id else ""
                typer.echo(f"{issue.code}{suffix}: {issue.message}", err=True)
            raise typer.Exit(1) from exc
        except (
            TransientError,
            OSError,
            ValueError,
            LookupError,
            NotImplementedError,
            ImportError,
            sqlite3.Error,
        ) as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(1) from exc

    return invoke


def _config(ctx: typer.Context) -> RecoupConfig:
    config = RecoupConfig.from_env()
    if ctx.obj and ctx.obj.get("db") is not None:
        config = config.model_copy(update={"db": ctx.obj["db"]})
    return config


def _provenance(config: RecoupConfig, provider: str) -> None:
    typer.echo(f"SYNTHETIC data | MOCK actions | LLM {config.llm} | runtime {provider}")
    if provider == "contract-stubs":
        typer.echo(
            "Engine unavailable: contract stubs; investigation and finance-validator "
            "integration await Sonny 007-4/5 (G3)."
        )


@contextmanager
def _service(ctx: typer.Context):
    service = build(_config(ctx))
    try:
        _provenance(service.config, getattr(service, "runtime_provider", "injected"))
        yield service
    finally:
        close = getattr(service.world, "close", None)
        if close is not None:
            close()


def _json(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _show(value) -> None:
    typer.echo(json.dumps(value, default=_json, ensure_ascii=False, indent=2))


def _lines(entries: list[str] | None) -> list[LineAmount] | None:
    if entries is None:
        return None
    result = []
    seen = set()
    for entry in entries:
        line_id, separator, amount = entry.partition("=")
        line_id = line_id.strip()
        if not separator or not line_id:
            raise ValueError(f"Expected LINE=CENTS, got {entry!r}")
        try:
            cents = int(amount)
        except ValueError as exc:
            raise ValueError(f"CENTS must be an integer in {entry!r}") from exc
        if cents < 0:
            raise ValueError("CENTS must be nonnegative")
        if line_id in seen:
            raise ValueError(f"Duplicate line allocation: {line_id}")
        seen.add(line_id)
        result.append(LineAmount(line_id=line_id, amount=Money(cents=cents)))
    return result


@app.callback()
def main(
    ctx: typer.Context,
    db: Annotated[
        str | None, typer.Option("--db", help="SQLite path; overrides RECOUP_DB.")
    ] = None,
) -> None:
    ctx.obj = {"db": db}


@app.command("init")
@_handled
def initialize(ctx: typer.Context) -> None:
    """Initialize the SQLite workbench."""
    with _service(ctx) as service:
        _show({"initialized": True, "db": service.config.db})


@app.command()
@_handled
def load(
    ctx: typer.Context, paths: Annotated[list[str], typer.Argument(metavar="PATH...")]
) -> None:
    """Load one or more bundle directories or directories of bundles."""
    with _service(ctx) as service:
        _show(service.load(paths))


@app.command("load-remittance")
@_handled
def load_remittance(ctx: typer.Context, bundle_json: Path) -> None:
    """Load synthetic historical cash allocation across explicitly referenced invoices."""
    with _service(ctx) as service:
        result = service.load_remittance(str(bundle_json))
        _show(result)
        if result.status != "loaded":
            raise typer.Exit(1)


@app.command()
@_handled
def run(ctx: typer.Context, case: Annotated[str | None, typer.Argument()] = None) -> None:
    """Run the selected controller and display the case(s)."""
    with _service(ctx) as service:
        _show(service.run(case))


@app.command()
@_handled
def advance(
    ctx: typer.Context,
    days: Annotated[int | None, typer.Argument(min=0)] = None,
    to_next_due: Annotated[bool, typer.Option("--to-next-due")] = False,
) -> None:
    """Advance the DEMO CLOCK and dispatch events and due work automatically."""
    with _service(ctx) as service:
        cases = service.advance(days=days, to_next_due=to_next_due)
        _show(
            {
                "clock": "DEMO CLOCK",
                "sim_day": service.world.clock.day(),
                "sim_now": service.world.clock.now(),
                "cases": cases,
            }
        )


@app.command("add-evidence")
@_handled
def add_evidence(ctx: typer.Context, case: str, doc_json: Path) -> None:
    """Attach a BundleDoc JSON; relative files resolve beside that JSON."""
    document = BundleDoc.model_validate_json(doc_json.read_text(encoding="utf-8"))
    with _service(ctx) as service:
        _show(service.add_evidence(case, document, str(doc_json.resolve().parent)))


@app.command("confirm-field")
@_handled
def confirm_field(ctx: typer.Context, evidence_id: str, key: str) -> None:
    """Append a human confirmation of a source or extracted field."""
    with _service(ctx) as service:
        _show(service.confirm_field(evidence_id, key))


@app.command()
@_handled
def edit(
    ctx: typer.Context,
    proposal: str,
    version: Annotated[int, typer.Argument(min=1)],
    text: Annotated[Path | None, typer.Option("--text", help="UTF-8 draft file.")] = None,
    line: Annotated[list[str] | None, typer.Option("--line", help="Repeat LINE=CENTS.")] = None,
    recipient: Annotated[str | None, typer.Option("--recipient")] = None,
) -> None:
    """Create a revised proposal with text, recipient or reduced allocations."""
    changes = {}
    if text is not None:
        changes["draft_text"] = text.read_text(encoding="utf-8")
    allocations = _lines(line)
    if allocations is not None:
        changes["allocations"] = allocations
    if recipient is not None:
        changes["recipient"] = recipient
    with _service(ctx) as service:
        _show(service.edit(proposal, version, **changes))


@app.command()
@_handled
def approve(
    ctx: typer.Context, proposal: str, version: Annotated[int, typer.Argument(min=1)]
) -> None:
    """Approve this exact proposal version for a later mock submission."""
    with _service(ctx) as service:
        _show(service.approve(proposal, version))


@app.command()
@_handled
def reject(
    ctx: typer.Context,
    proposal: str,
    version: Annotated[int, typer.Argument(min=1)],
    reason: Annotated[str, typer.Option("--reason")],
) -> None:
    """Reject a proposal with an audit reason."""
    if not reason.strip():
        raise ValueError("Rejection reason must not be blank")
    with _service(ctx) as service:
        _show(service.reject(proposal, version, reason))


@app.command()
@_handled
def submit(
    ctx: typer.Context, proposal: str, version: Annotated[int, typer.Argument(min=1)]
) -> None:
    """Submit an approved version to its mock target."""
    with _service(ctx) as service:
        _show(service.submit(proposal, version))


@app.command()
@_handled
def status(ctx: typer.Context, case: Annotated[str | None, typer.Argument()] = None) -> None:
    """Display current cases and quarantined bundles."""
    with _service(ctx) as service:
        _show(
            service.world.view(case)
            if case is not None
            else {
                "cases": service.world.list_cases(),
                "quarantined": service.world.list_quarantined(),
            }
        )


@app.command()
@_handled
def history(ctx: typer.Context, case: str) -> None:
    """Display immutable evidence, revisions, approvals, attempts and MOCK receipts."""
    with _service(ctx) as service:
        _show(service.history(case))


@app.command()
@_handled
def doctor(ctx: typer.Context) -> None:
    """Report local capability checks without opening a DB or contacting providers."""
    config = _config(ctx)
    _provenance(config, "diagnostics")
    caps = scan_capabilities(llm_mode=config.llm, vision=config.vision)
    ocr_packages = caps["pytesseract"] and caps["pillow"]
    executable = caps["tesseract"]
    image_ocr = bool(ocr_packages and executable)
    _show(
        {
            "engine_installed": find_spec("recoup.engine") is not None,
            "text_layer_pdf": caps["pypdf"],
            "capabilities": caps,
            "ocr": {
                "python_packages": ocr_packages,
                "tesseract_executable": executable,
                "available": image_ocr,
                "pdf_renderer": caps["pdf_renderer"],
                "scanned_pdf_available": bool(image_ocr and caps["pypdf"] and caps["pdf_renderer"]),
            },
            "vision": {
                "requested": config.vision,
                "api_key_configured": bool(os.environ.get("OPENAI_API_KEY")),
                "available": bool(caps["vision"] and caps["pillow"]),
                "status": "Requires engine/provider support; not verified by this local check.",
            },
            "network_checked": False,
        }
    )


@app.command("check-regression")
@_handled
def check_regression(
    ctx: typer.Context,
    cases_dir: Annotated[str, typer.Option("--cases-dir")] = "cases/regression",
) -> None:
    """Compare regression cases to their oracles; exit 1 on any mismatch."""
    with _service(ctx) as service:
        results = service.check_regression(cases_dir)
        _show(
            [
                {"case_id": case, "passed": passed, "errors": errors}
                for case, passed, errors in results
            ]
        )
        if not results:
            typer.echo("Error: no regression cases were evaluated", err=True)
            raise typer.Exit(1)
        if any(not passed for _, passed, _ in results):
            raise typer.Exit(1)


if __name__ == "__main__":
    app()
