"""Queue ordering and presentation, without importing Streamlit."""

from datetime import datetime, timedelta, timezone

import pytest

from recoup.contracts.bundle import CaseBundle
from recoup.contracts.models import CaseStatus, DueWork
from recoup.contracts.money import Money
from recoup.ui.queue import (
    format_case,
    format_clock,
    format_quarantine,
    next_due_at,
    sort_cases,
)


def work(case_id, due_at, status="pending"):
    return DueWork(
        due_id=f"{case_id}-{status}",
        case_id=case_id,
        kind="follow_up",
        due_at=due_at,
        basis="SYNTHETIC test",
        status=status,
        idempotency_key=f"{case_id}-{status}",
    )


def test_sort_pending_due_then_balance_with_undated_last(service):
    base = service.world.view("H")
    now = base.sim_now
    cases = [
        base.model_copy(
            update={
                "case_id": case_id,
                "open_balance": Money(cents=cents),
                "due": [work(case_id, now + timedelta(days=day))] if day is not None else [],
            }
        )
        for case_id, day, cents in [
            ("undated-small", None, 1),
            ("later", 2, 999999),
            ("same-small", 1, 100),
            ("same-large-b", 1, 200),
            ("undated-large", None, 9999999),
            ("overdue", -1, 0),
            ("same-large-a", 1, 200),
        ]
    ]
    original = cases.copy()
    assert [case.case_id for case in sort_cases(iter(cases))] == [
        "overdue",
        "same-large-a",
        "same-large-b",
        "same-small",
        "later",
        "undated-large",
        "undated-small",
    ]
    assert cases == original
    assert sort_cases([]) == []


def test_nearest_due_ignores_finished_and_cancelled_work(service):
    case = service.world.view("H")
    now = case.sim_now
    case = case.model_copy(
        update={
            "due": [
                work("H", now - timedelta(days=3), "done"),
                work("H", now - timedelta(days=2), "cancelled"),
                work("H", now + timedelta(days=4)),
                work("H", now + timedelta(days=1)),
            ]
        }
    )
    assert next_due_at(case) == now + timedelta(days=1)
    assert next_due_at(case.model_copy(update={"due": case.due[:2]})) is None
    assert next_due_at(case.model_copy(update={"due": []})) is None


def test_due_dates_compare_in_utc_with_time_precision(service):
    case = service.world.view("H")
    now = case.sim_now
    local_time = (now + timedelta(hours=1)).astimezone(timezone(timedelta(hours=-7)))
    case = case.model_copy(
        update={
            "due": [
                work("H", local_time),
                work("H", now.replace(tzinfo=None) + timedelta(hours=2)),
            ]
        }
    )
    assert next_due_at(case) == now + timedelta(hours=1)
    assert format_case(case)["Next due (UTC)"] == "2026-10-20 01:00"


@pytest.mark.parametrize(
    ("cents", "expected"),
    [
        (0, "$0.00"),
        (1, "$0.01"),
        (-101, "-$1.01"),
        (123456789, "$1,234,567.89"),
        (100000000000000001, "$1,000,000,000,000,000.01"),
    ],
)
def test_case_formatting_preserves_integer_cents(service, cents, expected):
    case = service.world.view("H").model_copy(
        update={"open_balance": Money(cents=cents), "due": [], "status": CaseStatus.needs_info}
    )
    row = format_case(case)
    assert row["Open balance (USD)"] == expected
    assert row["Case"] == "H"
    assert row["Title"] == case.title
    assert row["Buyer"] == case.buyer
    assert row["Status"] == "needs info"
    assert row["Next due (UTC)"] == "No pending due date"
    assert "total" not in " ".join(row).lower()


def test_clock_uses_simulated_date():
    assert format_clock(9, datetime(2026, 10, 29, tzinfo=timezone.utc)) == (
        "DEMO CLOCK: day 9 (2026-10-29, simulated)"
    )


def test_quarantined_currency_is_separate_and_has_no_money(service, tmp_path):
    bundle = CaseBundle(
        case_id="EUR-UI",
        title="SYNTHETIC quarantine test",
        seller="Seller",
        buyer="Buyer",
        currency="EUR",
        invoice_ref="INV-EUR",
        start_date=service.world.clock.now().date(),
        docs=[],
    )
    (tmp_path / "bundle.json").write_text(bundle.model_dump_json())
    assert service.load([str(tmp_path)])[0].status == "quarantined"
    record = service.world.list_quarantined()[0]
    row = format_quarantine(record)
    assert row == {
        "Case": "EUR-UI",
        "Reason": record.reason,
        "Quarantined at": record.at.isoformat(),
    }
    assert "EUR-UI" not in [case.case_id for case in sort_cases(service.world.list_cases())]
    assert all("$" not in value for value in row.values())
    assert "raw_bundle_json" not in row
