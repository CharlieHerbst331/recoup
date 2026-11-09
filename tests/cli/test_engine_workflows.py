"""Persisted CLI acceptance with the installed engine and real financial gates."""

import json
from pathlib import Path

from typer.testing import CliRunner

from recoup import cli

runner = CliRunner()
ROOT = Path(__file__).resolve().parents[2]


def test_real_cli_approval_mock_receipt_replay_and_day_three_reconsideration(tmp_path):
    db = tmp_path / "actual-engine.db"

    def command(*args):
        result = runner.invoke(cli.app, ["--db", str(db), *map(str, args)])
        assert result.exit_code == 0, result.output
        assert "SYNTHETIC data | MOCK actions | LLM fake | runtime engine" in result.output
        return json.loads(result.output.split("\n", 1)[1])

    def view():
        return command("status", "H")

    def proposal(kind):
        return next(
            p for p in view()["proposals"] if p["kind"] == kind and p["status"] == "proposed"
        )

    def submit(p):
        command("approve", p["proposal_id"], p["version"])
        return command("submit", p["proposal_id"], p["version"])

    command("load", ROOT / "cases/demo/H")
    assert view()["open_balance"]["cents"] == 624000
    submit(proposal("credit_memo"))
    assert view()["open_balance"]["cents"] == 444000
    dispute = proposal("dispute")
    text = tmp_path / "dispute.txt"
    text.write_text(dispute["draft_text"] + "\nPlease review the cited documents.")
    edited = command("edit", dispute["proposal_id"], dispute["version"], "--text", text)
    original = submit(edited)
    assert original["receipt_id"].startswith("MOCK-")
    replay = command("submit", edited["proposal_id"], edited["version"])
    assert replay == original
    advanced = command("advance", "--to-next-due")
    assert advanced["sim_day"] == 3
    correction = proposal("correction")
    assert correction["corrects_receipt_id"] == original["receipt_id"]
    assert correction["amount"]["cents"] == 312000
    submit(correction)
    increment = proposal("credit_memo")
    assert increment["amount"]["cents"] == 312000
    submit(increment)
    assert view()["open_balance"]["cents"] == 132000
    history = command("history", "H")
    assert original in history["receipts"]
    assert (
        sum(
            entry["amount"]["cents"]
            for entry in history["ledger"]
            if entry["kind"] == "credit_posted"
        )
        == 492000
    )
    assert sum(attempt["outcome"] == "idempotent_return" for attempt in history["attempts"]) == 1
