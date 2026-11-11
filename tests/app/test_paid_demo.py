"""SYNTHETIC paid-demo acceptance; design/02 §3.7, §4.5, §5.3–5.9."""

from datetime import date
from pathlib import Path

import pytest

from recoup.app import RecoupConfig, build
from recoup.contracts.bundle import CaseBundle
from recoup.contracts.money import Money
from recoup.world.store import SqliteWorld

DEMO = Path(__file__).resolve().parents[2] / "cases/demo"
PAID = {"PAID-FULL": (125000, [125000]), "PAID-INSTALLMENTS": (240000, [90000, 150000])}


@pytest.fixture
def service():
    app = build(RecoupConfig(db=":memory:", llm="fake"))
    assert app.runtime_provider == "engine"
    assert app.llm.mode == "fake" and app.llm.model_id == "offline-fakellm"
    assert isinstance(app.world, SqliteWorld)
    try:
        yield app
    finally:
        app.world.close()


def assert_paid(service, case_id):
    total, payments = PAID[case_id]
    view = service.world.view(case_id)
    assert view.provenance == "synthetic"
    assert view.invoice_total == Money(cents=total)
    assert view.open_balance == service.world.ledger_balance(case_id) == Money(cents=0)
    assert view.lines == []  # Includes absence of U1 and NP; design/02 §3.7.
    assert view.decision is not None and view.decision.current
    assert view.decision.lines == []
    assert view.decision.llm_mode == "fake"
    assert view.status != "needs_human", view.status_reason
    assert view.proposals == view.receipts == view.due == []
    history = service.history(case_id)
    assert history.proposals_all == history.approvals == history.receipts == history.attempts == []
    assert sorted((e.kind, e.amount.cents) for e in history.ledger) == sorted(
        [("invoice", total), *(("payment", cents) for cents in payments)]
    )
    tools = [trace for trace in history.traces if trace.kind == "tool_call"]
    assert tools and all(trace.result["ok"] for trace in tools)
    assert {trace.tool for trace in tools} >= {
        "list_evidence",
        "read_evidence",
        "run_rules",
        "propose_decision",
        "end",
    }
    assert all(
        trace.result["result"]["findings"] == [] for trace in tools if trace.tool == "run_rules"
    )
    assert any(trace.tool == "end" and trace.result["result"]["accepted"] for trace in tools)
    assert {trace.args["evidence_id"] for trace in tools if trace.tool == "read_evidence"} == {
        evidence.evidence_id for evidence in view.evidence
    }
    models = [trace for trace in history.traces if trace.kind == "model_call"]
    assert models and all(trace.llm_mode == "fake" for trace in models)
    assert service.rules_only(case_id).lines == []
    assert service.static_output(case_id).proposals == []


@pytest.mark.parametrize("case_id", PAID)
def test_paid_demo_normal_intake_rules_agent_and_repeat_load(service, case_id):
    path = str(DEMO / case_id)
    assert service.load([path])[0].status == "loaded"
    assert_paid(service, case_id)
    before = service.history(case_id)
    due = service.world.view(case_id).due
    service.load([path])
    assert_paid(service, case_id)
    after = service.history(case_id)
    # Repeat loading may add audit traces; saved decisions and economic state stay stable.
    for field in (
        "evidence_all",
        "facts",
        "reasons",
        "decisions",
        "proposals_all",
        "approvals",
        "receipts",
        "attempts",
        "ledger",
    ):
        assert getattr(after, field) == getattr(before, field), field
    assert service.world.view(case_id).due == due
    service.run(case_id)
    service.advance(days=15)
    assert_paid(service, case_id)


def test_whole_demo_load_preserves_flagged_cases_and_is_idempotent(service):
    results = service.load([str(DEMO)])
    assert {r.case_id for r in results} == {"H", "C", "N", *PAID}
    assert all(r.status == "loaded" for r in results)
    for case_id in PAID:
        assert_paid(service, case_id)
    expected = {
        "H": (624000, {("credit_memo", 180000), ("dispute", 444000), ("insurer_notice", None)}),
        "C": (50000, {("credit_memo", 50000)}),
        "N": (215000, {("info_request", None)}),
    }
    for case_id, (balance, proposals) in expected.items():
        view = service.world.view(case_id)
        assert view.open_balance == Money(cents=balance)
        assert view.status != "needs_human", view.status_reason
        assert {
            (p.kind.value, p.amount.cents if p.amount else None) for p in view.proposals
        } == proposals
    assert [line.line_id for line in service.world.view("N").lines] == ["U1"]
    before = {cid: service.world.view(cid) for cid in {"H", "C", "N", *PAID}}
    ledgers = {cid: service.world.ledger(cid) for cid in before}
    service.load([str(DEMO)])
    assert {cid: service.world.view(cid) for cid in before} == before
    assert {cid: service.world.ledger(cid) for cid in before} == ledgers


def test_paid_demo_source_evidence_and_distinct_references():
    bundles = [
        CaseBundle.model_validate_json((DEMO / cid / "bundle.json").read_text()) for cid in PAID
    ]
    references = []
    for bundle in bundles:
        total, amounts = PAID[bundle.case_id]
        assert bundle.currency == "USD" and bundle.provenance == "synthetic"
        assert bundle.events == [] and bundle.static_day == 0
        assert bundle.title.startswith("SYNTHETIC")
        invoice, *payments = bundle.docs
        assert invoice.kind == "invoice" and invoice.fields["total_cents"] == total
        assert invoice.fields["buyer_id"] == bundle.buyer
        assert invoice.fields["invoice_no"] == bundle.invoice_ref
        assert invoice.fields["line.1.qty"] * invoice.fields["line.1.unit_price_cents"] == total
        assert [payment.fields["paid_cents"] for payment in payments] == amounts
        references.extend([bundle.case_id, bundle.invoice_ref, bundle.buyer])
        for payment in payments:
            assert payment.kind == "payment"
            assert payment.fields["invoice_no"] == bundle.invoice_ref
            assert payment.doc_ref == payment.fields["payment_ref"]
            references.append(payment.fields["payment_ref"])
            assert (
                date.fromisoformat(invoice.fields["invoice_date"])
                <= date.fromisoformat(payment.fields["paid_date"])
                <= date.fromisoformat(invoice.fields["due_date"])
                <= bundle.start_date
            )
        for doc in bundle.docs:
            assert doc.title.startswith("SYNTHETIC") and "SYNTHETIC" in doc.text
            assert doc.file is None and doc.held_by is None and doc.available_at_day == 0
            assert not any(key.startswith("ded.") for key in doc.fields)
            assert all(
                type(value) is int for key, value in doc.fields.items() if key.endswith("_cents")
            )
    assert len(references) == len(set(references))
    existing = [
        CaseBundle.model_validate_json((DEMO / cid / "bundle.json").read_text())
        for cid in ("H", "C", "N")
    ]
    assert set(references).isdisjoint(
        {ref for b in existing for ref in (b.case_id, b.invoice_ref, b.buyer)}
    )
