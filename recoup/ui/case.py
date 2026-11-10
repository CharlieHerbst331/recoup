"""Pure case presentation helpers for design/02 §6."""

from datetime import datetime, timezone

from recoup.contracts.models import CaseHistory, CaseView, Readiness
from recoup.contracts.money import Money, fmt


def money_table(case: CaseView) -> list[dict[str, str]]:
    decisions = {line.line_id: line for line in case.decision.lines} if case.decision else {}
    rows = [
        {
            "Item": label,
            "Amount (USD)": fmt(amount),
            "Claimed (USD)": "",
            "Verdict": "",
            "Valid (USD)": "",
            "Disputed (USD)": "",
        }
        for label, amount in (
            ("Invoice total", case.invoice_total),
            ("Open balance", case.open_balance),
        )
    ]
    for line in case.lines:
        decision = decisions.get(line.line_id)
        rows.append(
            {
                "Item": line.line_id,
                "Amount (USD)": "",
                "Claimed (USD)": fmt(line.claimed),
                "Verdict": decision.verdict.value if decision else "Pending decision",
                "Valid (USD)": _amount(decision.valid if decision else None),
                "Disputed (USD)": _amount(decision.disputed if decision else None),
            }
        )
    return rows


def group_readiness(case: CaseView) -> dict[str, list[Readiness]]:
    return {
        kind: [record for record in case.readiness if record.kind == kind]
        for kind in ("dispute", "notice", "claim")
    }


def _amount(amount: Money | None) -> str:
    return fmt(amount) if amount is not None else "Unknown"


def _utc(at: datetime) -> datetime:
    return at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at.astimezone(timezone.utc)


def timeline_rows(history: CaseHistory) -> list[dict[str, str]]:
    """Use history snapshots, including superseded evidence and prior decisions."""
    entries: list[tuple[datetime, dict[str, str]]] = []

    def add(at: datetime, kind: str, reference: str, detail: str) -> None:
        at = _utc(at)
        entries.append(
            (
                at,
                {
                    "At (UTC)": at.isoformat(),
                    "Type": kind,
                    "Reference": reference,
                    "Detail": detail,
                },
            )
        )

    for evidence in history.evidence_all:
        state = "active" if evidence.active else "superseded"
        add(
            evidence.available_from,
            "Evidence",
            evidence.evidence_id,
            f"{evidence.doc_ref} v{evidence.version}: {evidence.title}; {state}; "
            f"available from this time; method={evidence.method.value}; "
            f"readable={evidence.readable}; "
            f"failure={evidence.failure.value if evidence.failure else 'none'}"
            + (f"; superseded by {evidence.superseded_by}" if evidence.superseded_by else ""),
        )
    for decision in history.decisions:
        lines = "; ".join(f"{line.line_id}: {line.verdict.value}" for line in decision.lines)
        add(
            decision.created_at,
            "Decision",
            decision.decision_id,
            f"v{decision.version}; current={decision.current}; "
            f"LLM: {decision.llm_mode} ({decision.model_id}); {lines}",
        )
    for approval in history.approvals:
        add(
            approval.at,
            "Approval",
            approval.approval_id,
            f"{approval.proposal_id} v{approval.proposal_version}; "
            f"{'approved' if approval.approved else 'rejected'} by {approval.approver}; "
            f"recipient={approval.recipient}; amount={_amount(approval.amount)}; "
            f"reason={approval.reason or 'none'}; void={approval.void}"
            + (f"; void reason={approval.void_reason}" if approval.void_reason else ""),
        )
    for receipt in history.receipts:
        add(
            receipt.at,
            "MOCK receipt",
            receipt.receipt_id,
            f"{receipt.label}; {receipt.proposal_id} v{receipt.proposal_version}; "
            f"target={receipt.target.value}; amount={_amount(receipt.amount)}",
        )
    for event in sorted(history.events, key=lambda event: event.seq):
        add(
            event.at,
            "Event",
            event.event_id,
            f"#{event.seq} {event.type}; ref={event.ref}; processed={event.processed}",
        )
    # Stable sorting preserves history order at equal times, including event sequence.
    return [row for _, row in sorted(entries, key=lambda entry: entry[0])]
