"""Command argument/output routing with counted ports; not G3 engine integration."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from recoup import cli
from recoup.app import RecoupConfig
from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import GateError, TransientError
from recoup.contracts.models import GateIssue

runner = CliRunner()


@pytest.fixture
def counted(monkeypatch):
    calls = []
    builds = []

    def operation(name):
        def invoke(*args, **kwargs):
            calls.append((name, args, kwargs))
            return {"called": name}

        return invoke

    world = SimpleNamespace(
        clock=SimpleNamespace(
            day=lambda: 3,
            now=lambda: datetime(2026, 10, 23, tzinfo=timezone.utc),
        ),
        close=operation("close"),
        view=operation("view"),
        list_cases=operation("list_cases"),
        list_quarantined=operation("list_quarantined"),
    )
    service = SimpleNamespace(
        config=RecoupConfig(db=":memory:"),
        world=world,
        runtime_provider="injected",
        **{
            name: operation(name)
            for name in (
                "load",
                "run",
                "advance",
                "add_evidence",
                "confirm_field",
                "edit",
                "approve",
                "reject",
                "submit",
                "history",
            )
        },
        check_regression=lambda cases_dir: [("r01", True, [])],
    )

    def build(config):
        builds.append(config)
        service.config = config
        return service

    monkeypatch.setattr(cli, "build", build)
    return service, calls, builds


@pytest.mark.parametrize(
    "arguments,name,args,kwargs",
    [
        (["load", "one", "two"], "load", (["one", "two"],), {}),
        (["run"], "run", (None,), {}),
        (["run", "CASE"], "run", ("CASE",), {}),
        (["advance"], "advance", (), {"days": None, "to_next_due": False}),
        (["advance", "2"], "advance", (), {"days": 2, "to_next_due": False}),
        (["advance", "--to-next-due"], "advance", (), {"days": None, "to_next_due": True}),
        (["confirm-field", "EV", "signed"], "confirm_field", ("EV", "signed"), {}),
        (["edit", "P", "2"], "edit", ("P", 2), {}),
        (["approve", "P", "2"], "approve", ("P", 2), {}),
        (["reject", "P", "2", "--reason", "Need POD"], "reject", ("P", 2, "Need POD"), {}),
        (["submit", "P", "2"], "submit", ("P", 2), {}),
        (["status", "CASE"], "view", ("CASE",), {}),
        (["history", "CASE"], "history", ("CASE",), {}),
    ],
)
def test_all_command_routes(counted, arguments, name, args, kwargs):
    _, calls, builds = counted
    result = runner.invoke(cli.app, ["--db", ":memory:", *arguments])
    assert result.exit_code == 0, result.output
    assert calls == [(name, args, kwargs), ("close", (), {})]
    assert len(builds) == 1
    assert builds[0].db == ":memory:"
    assert "SYNTHETIC data | MOCK actions | LLM fake | runtime injected" in result.output


def test_initialization_status_and_db_override(counted, monkeypatch):
    _, calls, builds = counted
    monkeypatch.setenv("RECOUP_DB", "environment.db")
    result = runner.invoke(cli.app, ["--db", ":memory:", "init"])
    assert result.exit_code == 0, result.output
    assert '"initialized": true' in result.output
    assert builds[-1].db == ":memory:"
    assert calls == [("close", (), {})]
    calls.clear()
    result = runner.invoke(cli.app, ["status"])
    assert result.exit_code == 0, result.output
    assert builds[-1].db == "environment.db"
    assert calls == [
        ("list_cases", (), {}),
        ("list_quarantined", (), {}),
        ("close", (), {}),
    ]


def test_document_and_full_edit_arguments(counted, tmp_path):
    _, calls, _ = counted
    doc = BundleDoc(doc_ref="POD", kind="pod", title="SYNTHETIC", text="Signed")
    path = tmp_path / "doc.json"
    path.write_text(doc.model_dump_json(), encoding="utf-8")
    result = runner.invoke(cli.app, ["add-evidence", "CASE", str(path)])
    assert result.exit_code == 0, result.output
    assert calls[0] == ("add_evidence", ("CASE", doc, str(tmp_path.resolve())), {})
    calls.clear()
    text = tmp_path / "draft.txt"
    text.write_text("SYNTHETIC MOCK revised text\n", encoding="utf-8")
    result = runner.invoke(
        cli.app,
        [
            "edit",
            "P",
            "1",
            "--text",
            str(text),
            "--line",
            "D1=123",
            "--line",
            "D2=0",
            "--recipient",
            "buyer@example.test",
        ],
    )
    assert result.exit_code == 0, result.output
    name, args, changes = calls[0]
    assert (name, args) == ("edit", ("P", 1))
    assert changes["draft_text"] == text.read_text()
    assert changes["recipient"] == "buyer@example.test"
    assert [(item.line_id, item.amount.cents) for item in changes["allocations"]] == [
        ("D1", 123),
        ("D2", 0),
    ]


@pytest.mark.parametrize("entry", ["D1=1.5", "D1=-1", "D1=abc", "=1", "D1"])
def test_invalid_allocations_fail_before_assembly(counted, entry):
    _, calls, builds = counted
    result = runner.invoke(cli.app, ["edit", "P", "1", "--line", entry])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert calls == builds == []


def test_duplicate_allocation_and_blank_rejection_fail_before_assembly(counted):
    _, calls, builds = counted
    result = runner.invoke(cli.app, ["edit", "P", "1", "--line", "D1=1", "--line", "D1=2"])
    assert result.exit_code == 1
    assert "Duplicate line" in result.output
    result = runner.invoke(cli.app, ["reject", "P", "1", "--reason", "  "])
    assert result.exit_code == 1
    assert calls == builds == []


@pytest.mark.parametrize(
    "arguments",
    [["load"], ["approve", "P", "0"], ["advance", "-1"], ["reject", "P", "1"]],
)
def test_usage_errors_exit_two(counted, arguments):
    _, calls, builds = counted
    result = runner.invoke(cli.app, arguments)
    assert result.exit_code == 2
    assert calls == builds == []


@pytest.mark.parametrize(
    "error,expected",
    [
        (
            GateError([GateIssue(code="not_approved", message="Need approval", line_id="D1")]),
            "not_approved [D1]: Need approval",
        ),
        (TransientError("MOCK unavailable"), "MOCK unavailable"),
        (NotImplementedError("Replay requires actual engine"), "Replay requires actual engine"),
        (ValueError("Bad selection"), "Bad selection"),
        (ImportError("Installed engine factory export is missing"), "factory export is missing"),
    ],
)
def test_domain_errors_are_readable_and_close_resources(counted, error, expected):
    service, calls, _ = counted

    def fail(*args, **kwargs):
        raise error

    service.submit = fail
    result = runner.invoke(cli.app, ["submit", "P", "1"])
    assert result.exit_code == 1
    assert expected in result.output
    assert calls == [("close", (), {})]


def test_file_and_json_errors_are_readable_before_assembly(counted, tmp_path):
    _, calls, builds = counted
    result = runner.invoke(cli.app, ["add-evidence", "CASE", str(tmp_path / "missing.json")])
    assert result.exit_code == 1
    assert "Error:" in result.output
    path = tmp_path / "bad.json"
    path.write_text("{}")
    result = runner.invoke(cli.app, ["add-evidence", "CASE", str(path)])
    assert result.exit_code == 1
    assert "validation errors" in result.output
    assert calls == builds == []


def test_regression_pass_and_failure_exit_codes(counted):
    service, calls, _ = counted
    directories = []

    def compare(directory):
        directories.append(directory)
        return [("r01", True, []), ("r02", False, ["wrong cents"])]

    service.check_regression = compare
    result = runner.invoke(cli.app, ["check-regression", "--cases-dir", "custom-cases"])
    assert result.exit_code == 1
    assert directories == ["custom-cases"]
    assert "wrong cents" in result.output
    assert '"case_id": "r02"' in result.output
    service.check_regression = lambda directory: [("r01", True, [])]
    assert runner.invoke(cli.app, ["check-regression"]).exit_code == 0
    service.check_regression = lambda directory: []
    result = runner.invoke(cli.app, ["check-regression"])
    assert result.exit_code == 1
    assert "no regression cases" in result.output
    assert len(calls) == 3


def test_doctor_without_assembly_database_network_or_secret_output(counted, tmp_path, monkeypatch):
    _, calls, builds = counted
    secret = "CLI-TEST-KEY-DO-NOT-PRINT"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    monkeypatch.setenv("RECOUP_VISION", "true")
    path = tmp_path / "never-created.db"
    monkeypatch.setattr(cli, "find_spec", lambda name: None)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    result = runner.invoke(cli.app, ["--db", str(path), "doctor"])
    assert result.exit_code == 0, result.output
    assert '"engine_installed": false' in result.output
    assert '"available": false' in result.output
    assert '"requested": true' in result.output
    assert '"api_key_configured": true' in result.output
    assert secret not in result.output
    assert not path.exists()
    assert calls == builds == []


def test_stub_provider_is_honestly_labeled(counted):
    service, _, _ = counted
    service.runtime_provider = "contract-stubs"
    result = runner.invoke(cli.app, ["run"])
    assert result.exit_code == 0
    assert "Engine unavailable" in result.output
    assert "contract stubs" in result.output
    assert "finance-validator integration await" in result.output


def test_unexpected_programming_error_is_not_hidden(counted):
    service, calls, _ = counted

    def fail(*args):
        raise RuntimeError("installed provider bug")

    service.run = fail
    result = runner.invoke(cli.app, ["run"])
    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "installed provider bug"
    assert calls == [("close", (), {})]
