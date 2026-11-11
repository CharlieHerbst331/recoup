"""Offline fixture validation through app.build; design/02 §3.6–3.7, §5.6."""

from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import CaseBundle
from recoup.contracts.testing import NullController
from recoup.engine.rules import run_rules

FIXTURE = Path(__file__).resolve().parents[2] / "cases/unseen/alder-2718"
CASE = "ALDER-2718"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Fixture tests must remain offline")

    monkeypatch.setattr("socket.socket.connect", blocked)
    monkeypatch.setattr("socket.create_connection", blocked)


def test_source_only_bundle_and_supersession():
    raw = (FIXTURE / "bundle.json").read_text()
    bundle = CaseBundle.model_validate_json(raw)
    assert bundle.provenance == "synthetic" and bundle.events == []
    assert all(d.file is None and d.held_by is None for d in bundle.docs)
    assert all("SYNTHETIC" in d.title for d in bundle.docs)
    assert all(type(v) is int for d in bundle.docs for k, v in d.fields.items() if "cents" in k)
    assert not any(
        word in raw for word in ('"decisions"', '"proposals"', '"rationale"', '"traces"')
    )
    app = build(RecoupConfig(db=":memory:", llm="fake"), controller=NullController())
    try:
        assert app.load([str(FIXTURE)])[0].status == "loaded"
        history = app.history(CASE)
        assert not history.decisions and not history.proposals_all
        assert not any(t.kind in {"model_call", "tool_call"} for t in history.traces)
        pods = sorted(
            (e for e in history.evidence_all if e.doc_ref == "ALDER-POD-2718"),
            key=lambda e: e.version,
        )
        assert len(pods) == 2
        assert not pods[0].active and pods[0].superseded_by == pods[1].evidence_id
        assert pods[1].active and pods[1].fields["received.OAT-CASE"] == 112
        view = app.world.view(CASE)
        assert view.invoice_total.cents == 1260000 and view.open_balance.cents == 107200
        findings = {
            f.line_id: f
            for f in run_rules(view.lines, app.world.fact_set(CASE), app.world.ledger(CASE))
        }
        assert (findings["AM-SHORT"].verdict, findings["AM-SHORT"].valid.cents) == ("valid", 52000)
        assert (findings["AM-DISC"].verdict, findings["AM-DISC"].disputed.cents) == (
            "invalid",
            25200,
        )
        gap = findings["AM-DAMAGE"]
        assert gap.verdict == "needs_info" and gap.valid is None and gap.disputed is None
        assert "refused.BROTH-CASE" in gap.missing
        assert all(
            c.evidence_id != pods[0].evidence_id for f in findings.values() for c in f.citations
        )
    finally:
        app.world.close()


def test_normal_offline_load_completes_without_approval():
    app = build(RecoupConfig(db=":memory:", llm="fake"))
    try:
        assert app.load([str(FIXTURE)])[0].status == "loaded"
        view = app.world.view(CASE)
        assert view.decision and view.decision.current
        assert len(view.decision.lines) == 3
        assert {(p.kind.value, p.amount.cents if p.amount else None) for p in view.proposals} == {
            ("credit_memo", 52000),
            ("dispute", 25200),
            ("info_request", None),
        }
        session = app.tool_session(CASE, "offline-completion-check", "harness")
        assert session.call("end", {"reason": "Offline fixture validation"}).result == {
            "accepted": True,
            "unmet": [],
        }
        history = app.history(CASE)
        assert not history.approvals and not history.receipts and not history.attempts
        assert view.open_balance.cents == 107200
        assert all(p.status == "proposed" for p in view.proposals)
        assert all(t.llm_mode == "fake" for t in history.traces if t.kind == "model_call")
    finally:
        app.world.close()
