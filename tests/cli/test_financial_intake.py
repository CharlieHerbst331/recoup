"""CLI intake and diagnostics use shared contracts and real offline assembly."""

import json
from pathlib import Path

from typer.testing import CliRunner

from recoup import cli
from recoup.app import RecoupConfig, build

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_remittance_command_posts_once_and_persists_audit(tmp_path):
    db = tmp_path / "intake.db"
    source = ROOT / "cases/ambition/multi-invoice/remittance.json"
    args = ["--db", str(db), "load-remittance", str(source)]
    first = runner.invoke(cli.app, args)
    assert first.exit_code == 0, first.output
    assert '"unapplied": {' in first.output
    assert '"cents": 3000' in first.output
    second = runner.invoke(cli.app, args)
    assert second.exit_code == 0, second.output
    assert '"replay": true' in second.output
    service = build(RecoupConfig(db=str(db)))
    try:
        assert service.world.ledger_balance("ALLOC-A").cents == 0
        assert service.world.ledger_balance("ALLOC-B").cents == 5000
        assert len(service.world.remittance_history()) == 1
        assert len([e for e in service.world.ledger("ALLOC-B") if e.kind == "payment"]) == 1
    finally:
        service.world.close()


def test_invalid_remittance_exits_nonzero_without_child_cases(tmp_path):
    source = json.loads((ROOT / "cases/ambition/multi-invoice/remittance.json").read_text())
    source["allocations"][0]["invoice_no"] = "UNKNOWN"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(source))
    db = tmp_path / "intake.db"
    result = runner.invoke(cli.app, ["--db", str(db), "load-remittance", str(path)])
    assert result.exit_code == 1
    assert '"status": "needs_info"' in result.output
    service = build(RecoupConfig(db=str(db)))
    try:
        assert service.world.list_cases() == []
        assert service.world.remittance_history()[0].status == "needs_info"
    finally:
        service.world.close()


def test_doctor_reports_image_and_pdf_prerequisites_separately(monkeypatch):
    monkeypatch.setattr(
        cli,
        "scan_capabilities",
        lambda **kwargs: {
            "pypdf": True,
            "pillow": True,
            "tesseract": True,
            "pytesseract": True,
            "pdf_renderer": False,
            "vision": False,
            "llm_mode": "fake",
        },
    )
    result = runner.invoke(cli.app, ["doctor"])
    assert result.exit_code == 0
    report = json.loads(result.output.split("\n", 1)[1])
    assert report["ocr"]["available"] is True
    assert report["ocr"]["scanned_pdf_available"] is False
    assert report["text_layer_pdf"] is True
    assert report["network_checked"] is False
