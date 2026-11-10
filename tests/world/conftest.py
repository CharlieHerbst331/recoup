import socket
from datetime import date

import pytest

from recoup.contracts.bundle import BundleDoc, CaseBundle
from recoup.contracts.testing import stub_parts
from recoup.world import SqliteWorld


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("World tests must not access the network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


@pytest.fixture
def bundle():
    return CaseBundle(
        case_id="CASE",
        title="SYNTHETIC case",
        seller="Seller",
        buyer="Buyer",
        currency="USD",
        invoice_ref="INV",
        start_date=date(2026, 10, 20),
        allowed_recipients={"mock_email": ["buyer@example.test"], "mock_erp": ["ERP"]},
        docs=[
            BundleDoc(
                doc_ref="INV",
                kind="invoice",
                title="Invoice",
                fields={"total_cents": 10000, "due_date": "2026-10-19", "invoice_no": "INV"},
            ),
            BundleDoc(doc_ref="PAY", kind="payment", title="Payment", fields={"paid_cents": 8000}),
            BundleDoc(
                doc_ref="POD",
                kind="pod",
                title="POD",
                text="Received 80 cases. Received 90 cases.",
                fields={"signed": True},
            ),
        ],
    )


@pytest.fixture
def world():
    parts = stub_parts()
    world = SqliteWorld(":memory:", ingestor=parts.ingestor, validator=parts.validator)
    yield world
    world.close()
