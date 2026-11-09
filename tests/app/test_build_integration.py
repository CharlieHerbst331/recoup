"""G1: real SQLite with explicit contract stubs (design/02 §4.5)."""

from datetime import date

import pytest

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.models import DocKind
from recoup.contracts.testing import NullController


@pytest.fixture(autouse=True)
def contract_stub_runtime(monkeypatch):
    import recoup.app as module

    # These tests target G1 assembly, independently of installed engine providers.
    monkeypatch.setattr(module, "find_spec", lambda name: None)


def synthetic_bundle():
    return CaseBundle(
        case_id="APP-G1",
        title="SYNTHETIC app integration",
        seller="Seller",
        buyer="Buyer",
        currency="USD",
        invoice_ref="invoice",
        start_date=date(2026, 10, 20),
        docs=[
            BundleDoc(
                doc_ref="invoice",
                kind=DocKind.invoice,
                title="SYNTHETIC invoice",
                fields={"invoice_no": "I-G1", "total_cents": 10000, "due_date": "2026-09-02"},
            ),
            BundleDoc(
                doc_ref="payment",
                kind=DocKind.payment,
                title="SYNTHETIC payment",
                fields={"paid_cents": 8000, "payment_ref": "PAY-G1"},
            ),
        ],
    )


def test_build_real_sqlite_world_with_contract_stubs():
    from recoup.app import RecoupConfig, build
    from recoup.world.store import SqliteWorld

    controller = NullController()
    service = build(RecoupConfig(db=":memory:"), controller=controller)
    assert isinstance(service.world, SqliteWorld)
    assert service.controller is controller
    assert service.world.list_cases() == []
    assert service.next_due_day() is None


def test_real_load_view_tool_session_and_reopen(tmp_path):
    from recoup.app import RecoupConfig, build

    directory = tmp_path / "case"
    directory.mkdir()
    (directory / "bundle.json").write_text(synthetic_bundle().model_dump_json())
    config = RecoupConfig(db=str(tmp_path / "app.db"))
    service = build(config)
    assert service.load([str(directory)])[0].status == "loaded"
    view = service.world.view("APP-G1")
    assert view.open_balance.cents == 2000
    assert [(line.line_id, line.claimed.cents) for line in view.lines] == [("U1", 2000)]
    assert service.run("APP-G1")[0].case_id == "APP-G1"
    envelope = service.tool_session("APP-G1", "RUN", "REF").call("list_evidence", {})
    assert envelope.ok
    assert len(envelope.result["rows"]) == 2
    assert build(config).world.view("APP-G1").open_balance.cents == 2000


def test_eur_load_is_quarantined_through_facade(tmp_path):
    from recoup.app import RecoupConfig, build

    bundle = synthetic_bundle().model_copy(update={"currency": "EUR"})
    (tmp_path / "bundle.json").write_text(bundle.model_dump_json())
    service = build(RecoupConfig(db=":memory:"))
    assert service.load([str(tmp_path)])[0].status == "quarantined"
    assert service.world.list_cases() == []
    assert service.world.list_quarantined()[0].case_id == "APP-G1"
