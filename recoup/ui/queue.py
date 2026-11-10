"""Pure queue presentation helpers for design/02 §6."""

from collections.abc import Iterable
from datetime import datetime, timezone

from recoup.contracts.models import CaseView, QuarantineRecord
from recoup.contracts.money import fmt


def next_due_at(case: CaseView) -> datetime | None:
    pending = [
        item.due_at.replace(tzinfo=timezone.utc)
        if item.due_at.tzinfo is None
        else item.due_at.astimezone(timezone.utc)
        for item in case.due
        if item.status == "pending"
    ]
    return min(pending, default=None)


def sort_cases(cases: Iterable[CaseView]) -> list[CaseView]:
    """Earliest pending work first, then largest balance, then case ID."""
    last = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(
        cases,
        key=lambda case: (next_due_at(case) or last, -case.open_balance.cents, case.case_id),
    )


def format_clock(day: int, now: datetime) -> str:
    return f"DEMO CLOCK: day {day} ({now.date().isoformat()}, simulated)"


def format_case(case: CaseView) -> dict[str, str]:
    due = next_due_at(case)
    return {
        "Case": case.case_id,
        "Title": case.title,
        "Buyer": case.buyer,
        "Status": case.status.value.replace("_", " "),
        "Status reason": case.status_reason,
        "Insurance": case.insurance.value.replace("_", " "),
        "Next due (UTC)": due.strftime("%Y-%m-%d %H:%M") if due else "No pending due date",
        "Open balance (USD)": fmt(case.open_balance),
    }


def format_quarantine(record: QuarantineRecord) -> dict[str, str]:
    return {
        "Case": record.case_id,
        "Reason": record.reason,
        "Quarantined at": record.at.isoformat(),
    }
