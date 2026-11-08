from datetime import datetime, timezone
from unittest.mock import create_autospec

import pytest

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import Clock, GateError, LLMClient, LLMResponse, World
from recoup.contracts.models import (
    CaseHistory,
    CaseView,
    DeductionLine,
    DocStatus,
    EffectiveFact,
    Evidence,
    FactRevision,
    FactSet,
    GateIssue,
)
from recoup.contracts.money import Money
from recoup.contracts.testing import NullController, ScriptedLLM, TextOnlyIngestor, stub_parts

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


@pytest.fixture
def world_port():
    world = create_autospec(World, instance=True)
    world.clock = create_autospec(Clock, instance=True)
    world.clock.now.return_value = NOW
    world.clock.day.return_value = 0
    lines = [
        DeductionLine(line_id=line_id, reason="shortage", claimed=Money(cents=100))
        for line_id in ["D1", "D2"]
    ]
    row = Evidence(
        evidence_id="EV-H-pod-v1",
        case_id="H",
        doc_ref="pod",
        version=1,
        kind="pod",
        title="POD",
        available_from=NOW,
        content_sha256="a" * 64,
        readable=True,
        method="structured",
        text="Signed POD",
        fields={"signed": True},
        active=True,
    )
    world.active_evidence.return_value = [row]
    world.fact_set.return_value = FactSet(
        case_id="H",
        basis_hash="basis",
        facts=[
            EffectiveFact(
                evidence_id=row.evidence_id,
                doc_kind=row.kind,
                doc_ref=row.doc_ref,
                key="signed",
                value=True,
                trust="source",
                origin="source",
                fact_id=None,
                citation={
                    "evidence_id": row.evidence_id,
                    "locator": "fields.signed",
                    "quote": "true",
                },
            )
        ],
        docs=[
            DocStatus(
                evidence_id=row.evidence_id,
                doc_ref=row.doc_ref,
                kind=row.kind,
                readable=True,
                failure=None,
            )
        ],
    )
    world.history.return_value = CaseHistory(
        case_id="H",
        evidence_all=[row],
        facts=[],
        reasons=[],
        decisions=[],
        proposals_all=[],
        approvals=[],
        receipts=[],
        attempts=[],
        ledger=[],
        events=[],
        traces=[],
    )
    world.deduction_lines.return_value = lines
    world.current_decision.return_value = None
    world.evidence_set_hash.return_value = "basis"
    view = CaseView(
        case_id="H",
        title="Case H",
        buyer="Buyer",
        status="open",
        insurance="none",
        sim_day=0,
        sim_now=NOW,
        invoice_total=Money(cents=1000),
        open_balance=Money(cents=200),
        lines=lines,
        decision=None,
        proposals=[],
        receipts=[],
        readiness=[],
        due=[],
        evidence=[row],
    )
    world.view.return_value = view
    return world


def test_stub_parts_engine_smoke(world_port):
    parts = stub_parts()
    llm = create_autospec(LLMClient, instance=True)
    assert parts.engine.investigate(world_port, "H", llm, "run-1") == world_port.view.return_value
    decision = world_port.save_decision.call_args.args[0]
    assert decision.case_id == "H"
    assert decision.evidence_set_hash == "basis"
    assert decision.version == 1
    assert decision.llm_mode == "fake"
    assert [line.line_id for line in decision.lines] == ["D1", "D2"]
    assert all(
        line.verdict == "needs_info"
        and line.basis == "missing_evidence"
        and line.valid is None
        and line.disputed is None
        for line in decision.lines
    )
    output = parts.engine.static_output(world_port, "H")
    assert output == parts.engine.rules_only(world_port, "H")
    assert all(
        line.verdict == "needs_info" and line.valid_cents is None and line.disputed_cents is None
        for line in output.lines
    )
    assert output.proposals == []
    assert set(output.missing) == {"D1", "D2"}
    assert parts.engine.handle(world_port, llm, "run-2") == []
    llm.next.assert_not_called()
    world_port.current_decision.return_value = decision
    parts.engine.investigate(world_port, "H", llm, "run-3")
    assert world_port.save_decision.call_args.args[0].version == 2


def test_validator_and_null_controller_smoke(world_port):
    parts = stub_parts()
    for stage in ["save", "approve", "submit"]:
        assert parts.validator.validate(world_port, None, stage) == []
    before = world_port.mock_calls.copy()
    controller = NullController()
    assert controller.name == "null"
    assert controller.react(world_port, [], "run") is None
    assert world_port.mock_calls == before


def test_text_only_ingestor_smoke():
    ingestor = TextOnlyIngestor()
    structured = BundleDoc(
        doc_ref="inv", kind="invoice", title="Invoice", fields={"total_cents": 100}
    )
    result = ingestor.ingest(structured, None)
    assert result.readable and result.method == "structured"
    assert result.fields == structured.fields and result.failure is None
    result.fields["total_cents"] = 200
    assert structured.fields["total_cents"] == 100
    text = ingestor.ingest(
        BundleDoc(doc_ref="email", kind="email", title="Email", text="Hello"), None
    )
    assert text.text == "Hello" and text.readable and text.method == "text"
    empty = ingestor.ingest(BundleDoc(doc_ref="empty", kind="other", title="Empty"), None)
    assert not empty.readable and empty.failure == "empty_text"
    file = ingestor.ingest(
        BundleDoc(doc_ref="pdf", kind="pod", title="PDF", file="missing.pdf"), "/unused"
    )
    assert not file.readable and file.failure == "unsupported" and file.text == ""


def test_stub_tool_session_smoke_and_traces(world_port):
    session = stub_parts().tools.open(world_port, "H", "run", "stub-test")
    assert {schema["name"] for schema in session.schemas()} == {"list_evidence", "read_evidence"}
    listed = session.call("list_evidence", {})
    assert listed.ok and listed.result["rows"][0]["field_keys"] == ["signed"]
    assert session.call("list_evidence", {"kind": "invoice"}).result["rows"] == []
    assert session.call("list_evidence", {"include_superseded": True}).ok
    read = session.call("read_evidence", {"evidence_id": "EV-H-pod-v1", "max_chars": 6})
    assert read.ok and read.result["text"] == "Signed" and read.result["truncated"]
    assert read.result["source_fields"] == {"signed": True}
    assert read.result["facts"][0]["key"] == "signed"
    field = session.call(
        "read_evidence", {"evidence_id": "EV-H-pod-v1", "locator": "fields.signed"}
    )
    assert field.ok and field.result["text"] == "true"
    unknown = session.call("read_evidence", {"evidence_id": "EV-OTHER-pod-v1"})
    assert not unknown.ok and unknown.issues[0].code == "unknown_evidence"
    invalid = session.call("read_evidence", {})
    assert not invalid.ok and invalid.issues[0].code == "invalid_args"
    unsupported = session.call("submit_approved", {})
    assert not unsupported.ok and unsupported.issues[0].code == "unsupported_tool"
    calls = world_port.trace.call_args_list
    assert len(calls) == 8
    for step, call in enumerate(calls, 1):
        trace = call.args[0]
        assert trace.step == step and trace.controller == "stub-test"
        assert trace.result is not None and "ok" in trace.result
    assert calls[-1].args[0].result == unsupported.model_dump(mode="json")


def test_text_only_ingestor_text_file(tmp_path):
    (tmp_path / "pod.txt").write_text("Signed POD", encoding="utf-8")
    doc = BundleDoc(doc_ref="pod", kind="pod", title="POD", file="pod.txt")
    result = TextOnlyIngestor().ingest(doc, str(tmp_path))
    assert result.readable and result.method == "text" and result.text == "Signed POD"
    assert result.failure is None
    (tmp_path / "pod.txt").write_bytes(b"\xff")
    failed = TextOnlyIngestor().ingest(doc, str(tmp_path))
    assert not failed.readable and failed.failure == "corrupt"
    assert failed.text == ""


def test_scripted_llm_smoke():
    first = LLMResponse(
        tool_calls=[{"id": "1", "name": "list_evidence", "arguments": {}}],
        model_id="script",
        mode="fake",
    )
    second = LLMResponse(tool_calls=[], text="done", model_id="script", mode="fake")
    llm = ScriptedLLM([first, second])
    assert llm.next("system", [], []) == first
    assert llm.next("system", [], []) == second
    with pytest.raises(StopIteration):
        llm.next("system", [], [])


def test_stub_read_fact_locator(world_port):
    basis = world_port.fact_set.return_value
    source = basis.facts[0]
    revision = FactRevision(
        fact_id="F-H-001",
        case_id="H",
        evidence_id=source.evidence_id,
        key="signed",
        value=True,
        trust="human_confirmed",
        citation=source.citation,
        at=NOW,
        by="user",
    )
    effective = source.model_copy(
        update={
            "origin": "fact",
            "fact_id": revision.fact_id,
            "citation": source.citation.model_copy(update={"locator": "fact:F-H-001"}),
        }
    )
    world_port.fact_set.return_value = basis.model_copy(update={"facts": [effective]})
    world_port.history.return_value.facts = [revision]
    session = stub_parts().tools.open(world_port, "H", "run", "stub-test")
    read = session.call(
        "read_evidence",
        {
            "evidence_id": source.evidence_id,
            "locator": "fact:F-H-001",
        },
    )
    assert read.ok and read.result["text"] == "true"
    invalid = session.call(
        "read_evidence",
        {
            "evidence_id": source.evidence_id,
            "locator": "fact:F-H-old",
        },
    )
    assert not invalid.ok and invalid.issues[0].code == "superseded_citation"
    assert world_port.trace.call_count == 2


def test_gate_error_exposes_issues():
    issue = GateIssue(code="blocked", message="Not approved", line_id="D1")
    error = GateError([issue])
    assert error.issues == [issue]
    assert "blocked" in str(error) and "Not approved" in str(error)
