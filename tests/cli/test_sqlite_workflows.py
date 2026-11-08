"""CLI against actual app-built SQLite; contract validator is not engine/G3 proof."""

from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from recoup import cli
from recoup.contracts.bundle import BundleDoc, BundleEvent, CaseBundle
from recoup.contracts.models import (
    Decision,
    LineAmount,
    LineDecision,
    Proposal,
    ProposalKind,
    Target,
)
from recoup.contracts.money import Money

runner = CliRunner()


def fixture_bundle(case_id="CASE", currency="USD"):
    return CaseBundle(
        case_id=case_id,
        title="SYNTHETIC CLI integration case",
        seller="Synthetic seller",
        buyer="Synthetic buyer",
        currency=currency,
        invoice_ref="INV-CLI",
        start_date=date(2026, 10, 20),
        allowed_recipients={"mock_erp": ["ERP"], "mock_email": ["buyer@example.test"]},
        docs=[
            BundleDoc(
                doc_ref="INV",
                kind="invoice",
                title="SYNTHETIC Invoice",
                fields={
                    "invoice_no": "INV-CLI",
                    "total_cents": 10000,
                    "due_date": "2026-10-19",
                },
            ),
            BundleDoc(
                doc_ref="PAY",
                kind="payment",
                title="SYNTHETIC Payment",
                fields={"paid_cents": 8000},
            ),
            BundleDoc(doc_ref="POD", kind="pod", title="SYNTHETIC POD", fields={"signed": True}),
        ],
    )


def write_bundle(directory, bundle):
    directory.mkdir(parents=True)
    (directory / "bundle.json").write_text(bundle.model_dump_json(), encoding="utf-8")
    return str(directory)


def invoke(database, *arguments):
    return runner.invoke(cli.app, ["--db", str(database), *arguments])


def inspect(database):
    from recoup.app import RecoupConfig, build

    return build(RecoupConfig(db=str(database)))


def seed_credit(database):
    service = inspect(database)
    world = service.world
    decision = world.save_decision(
        Decision(
            decision_id="D-CLI",
            case_id="CASE",
            version=1,
            evidence_set_hash=world.evidence_set_hash("CASE"),
            lines=[
                LineDecision(
                    line_id="U1",
                    verdict="valid",
                    basis="proven",
                    valid=Money(cents=2000),
                    disputed=Money(cents=0),
                    citations=[],
                    rationale="Explicit SQLite orchestration test decision",
                )
            ],
            current=True,
            model_id="test",
            llm_mode="fake",
            prompt_version="test",
            created_at=world.clock.now(),
        )
    )
    proposal = world.save_proposal(
        Proposal(
            proposal_id="P-CLI",
            business_key="CASE:credit_memo:U1",
            version=1,
            case_id="CASE",
            kind="credit_memo",
            target="mock_erp",
            recipient="ERP",
            allocations=[LineAmount(line_id="U1", amount=Money(cents=2000))],
            amount=Money(cents=2000),
            draft_text="SYNTHETIC / MOCK / LLM fake. Record adjustment.",
            draft_sha256="",
            citations=[],
            decision_id=decision.decision_id,
            decision_version=decision.version,
            evidence_set_hash=world.evidence_set_hash("CASE"),
            status="proposed",
            created_at=world.clock.now(),
            created_by="agent",
        )
    )
    world.close()
    return proposal


def test_load_two_paths_status_history_quarantine_and_init(tmp_path):
    database = tmp_path / "workbench.db"
    first = write_bundle(tmp_path / "a", fixture_bundle("FIRST"))
    second = write_bundle(tmp_path / "b", fixture_bundle("SECOND"))
    result = invoke(database, "init")
    assert result.exit_code == 0, result.output
    assert database.exists()
    result = invoke(database, "load", first, second)
    assert result.exit_code == 0, result.output
    assert '"case_id": "FIRST"' in result.output
    assert '"case_id": "SECOND"' in result.output
    assert "contract stubs" in result.output
    result = invoke(database, "status")
    assert result.exit_code == 0, result.output
    assert '"case_id": "FIRST"' in result.output
    assert '"cents": 2000' in result.output
    result = invoke(database, "history", "FIRST")
    assert result.exit_code == 0, result.output
    assert '"evidence_all"' in result.output
    assert '"ledger"' in result.output
    eur = write_bundle(tmp_path / "eur", fixture_bundle("EUR", "EUR"))
    assert invoke(database, "load", eur).exit_code == 0
    result = invoke(database, "status")
    assert '"quarantined": [' in result.output
    assert "Unsupported currency: EUR" in result.output
    result = invoke(database, "status", "EUR")
    assert result.exit_code == 1
    assert "unknown_case" in result.output


def test_advance_next_due_releases_events_and_dispatches_automatically(tmp_path, monkeypatch):
    from recoup.app import build

    class ProcessingController:
        name = "CLI-counted-controller"

        def __init__(self):
            self.days = []
            self.observations = []

        def react(self, world, events, run_id):
            self.days.append(world.clock.day())
            self.observations.extend((event.type, event.ref) for event in events)
            for event in world.pending_events():
                world.mark_event(event.event_id)

    controller = ProcessingController()
    monkeypatch.setattr(cli, "build", lambda config: build(config, controller=controller))
    bundle = fixture_bundle()
    bundle.events = [
        BundleEvent(
            at_day=3,
            type="add_doc",
            doc=BundleDoc(doc_ref="REPLY", kind="email", title="SYNTHETIC reply", text="Received"),
        )
    ]
    database = tmp_path / "clock.db"
    directory = write_bundle(tmp_path / "case", bundle)
    result = invoke(database, "load", directory)
    assert result.exit_code == 0, result.output
    controller.days.clear()
    controller.observations.clear()
    result = invoke(database, "advance", "--to-next-due")
    assert result.exit_code == 0, result.output
    assert '"sim_day": 3' in result.output
    assert "DEMO CLOCK" in result.output
    assert controller.days == [1, 2, 3]
    service = inspect(database)
    rows = service.world.active_evidence("CASE")
    reply = next(row for row in rows if row.doc_ref == "REPLY")
    assert ("evidence_added", reply.evidence_id) in controller.observations
    assert service.world.pending_events() == []
    service.world.close()
    controller.days.clear()
    result = invoke(database, "advance", "--to-next-due")
    assert result.exit_code == 0
    assert controller.days == []


def test_confirm_add_relative_text_edit_approve_submit_replay_and_reject(tmp_path):
    database = tmp_path / "actions.db"
    directory = write_bundle(tmp_path / "case", fixture_bundle())
    assert invoke(database, "load", directory).exit_code == 0
    service = inspect(database)
    evidence_id = next(
        row.evidence_id for row in service.world.active_evidence("CASE") if row.doc_ref == "POD"
    )
    service.world.close()
    result = invoke(database, "confirm-field", evidence_id, "signed")
    assert result.exit_code == 0, result.output
    assert '"trust": "human_confirmed"' in result.output
    extra = tmp_path / "extra"
    extra.mkdir()
    (extra / "message.txt").write_text("SYNTHETIC attached message", encoding="utf-8")
    doc = BundleDoc(doc_ref="EXTRA", kind="email", title="SYNTHETIC extra", file="message.txt")
    doc_json = extra / "doc.json"
    doc_json.write_text(doc.model_dump_json())
    result = invoke(database, "add-evidence", "CASE", str(doc_json))
    assert result.exit_code == 0, result.output
    assert "SYNTHETIC attached message" in result.output
    seed_credit(database)
    result = invoke(database, "submit", "P-CLI", "1")
    assert result.exit_code == 1
    assert "not_approved" in result.output
    draft = tmp_path / "edit.txt"
    draft.write_text("SYNTHETIC / MOCK / LLM fake. Adjust 1500 cents.", encoding="utf-8")
    result = invoke(database, "edit", "P-CLI", "1", "--text", str(draft), "--line", "U1=1500")
    assert result.exit_code == 0, result.output
    assert '"version": 2' in result.output
    result = invoke(database, "approve", "P-CLI", "2")
    assert result.exit_code == 0, result.output
    result = invoke(database, "submit", "P-CLI", "2")
    assert result.exit_code == 0, result.output
    assert "MOCK-CM-0001" in result.output
    assert "MOCK ACKNOWLEDGMENT — not sent to any real system" in result.output
    result = invoke(database, "submit", "P-CLI", "2")
    assert result.exit_code == 0, result.output
    assert "MOCK-CM-0001" in result.output
    result = invoke(database, "status", "CASE")
    assert result.exit_code == 0
    assert '"cents": 500' in result.output
    service = inspect(database)
    world = service.world
    assert len(world.history("CASE").receipts) == 1
    assert [attempt.outcome for attempt in world.history("CASE").attempts] == [
        "gate_rejected",
        "receipt",
        "idempotent_return",
    ]
    source = world.history("CASE").proposals_all[-1]
    rejected = world.save_proposal(
        source.model_copy(
            update={
                "proposal_id": "P-REJECT",
                "business_key": "CASE:info_request:U1",
                "version": 1,
                "kind": ProposalKind.info_request,
                "target": Target.mock_email,
                "recipient": "buyer@example.test",
                "amount": None,
                "allocations": [],
                "draft_text": "Please send the signed POD.",
            }
        )
    )
    world.close()
    result = invoke(database, "reject", rejected.proposal_id, "1", "--reason", "Already received")
    assert result.exit_code == 0, result.output
    assert '"approved": false' in result.output
    result = invoke(database, "history", "CASE")
    assert result.exit_code == 0
    assert "Already received" in result.output
    assert "idempotent_return" in result.output


def test_real_regression_gate_reports_stub_mismatches_and_quarantine(tmp_path):
    cases = Path(__file__).resolve().parents[2] / "cases" / "regression"
    result = invoke(tmp_path / "regression.db", "check-regression", "--cases-dir", str(cases))
    assert result.exit_code == 1, result.output
    assert "Engine unavailable" in result.output
    assert '"case_id": "r01"' in result.output
    assert '"case_id": "r08"' in result.output
    assert result.output.count('"passed": true') == 1
    assert result.output.count('"passed": false') == 7
