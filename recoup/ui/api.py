"""React presentation adapter; all case mutations use Recoup (design/02 §6)."""

import base64
import re
from pathlib import Path

from pydantic import BaseModel

from recoup.app import Recoup
from recoup.contracts.models import LineAmount
from recoup.contracts.money import Money, fmt
from recoup.ui.actions import proposal_groups
from recoup.ui.case import money_table, timeline_rows
from recoup.ui.dashboard import (
    approval_count,
    approved_count,
    case_tags,
    dashboard_counts,
    demo_next_step,
    needs_attention,
)
from recoup.ui.evidence import evidence_fields, evidence_versions, inject_document
from recoup.ui.queue import display_title, format_clock, next_due_at, sort_cases
from recoup.ui.reviewer import (
    agent_runs,
    brief,
    decision_changes,
    document_facts,
    initial_balance,
    journey,
    new_payments,
    policy_review,
    posted,
    reconciled,
)

DEMO_ROOT = Path(__file__).resolve().parent / "demo"


def wire(value):
    """Keep cents and large integers exact across the browser JSON boundary."""
    if isinstance(value, BaseModel):
        return wire(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {key: str(item) if key == "cents" else wire(item) for key, item in value.items()}
    if isinstance(value, list):
        return [wire(item) for item in value]
    if type(value) is int and abs(value) > 2**53 - 1:
        return str(value)
    return value


def dashboard_data(service: Recoup) -> dict:
    cases = sort_cases(service.world.list_cases())
    payments = {case.case_id: new_payments(case, service.history(case.case_id)) for case in cases}
    return {
        "clock": {
            "day": service.world.clock.day(),
            "date": service.world.clock.now().date().isoformat(),
            "label": format_clock(service.world.clock.day(), service.world.clock.now()),
            "next_due_day": service.next_due_day(),
        },
        "llm": service.config.llm,
        "database": service.config.db,
        "counts": dashboard_counts(cases),
        "next_step": demo_next_step(cases),
        "journey": journey(cases),
        "resolved_count": sum(reconciled(case) for case in cases),
        "new_payments": fmt(Money(cents=sum(amount.cents for amount in payments.values()))),
        "claims_submitted_count": sum(posted(case, "claim_package") for case in cases),
        "outcomes": [
            {
                "buyer": case.buyer,
                "case_id": case.case_id,
                "scenario": next(
                    (
                        e.fields["demo_outcome"]
                        for e in case.evidence
                        if e.active and e.fields.get("demo_outcome")
                    ),
                    "Case outcome",
                ),
                **brief(case),
                "balance": fmt(case.open_balance),
                "payments": fmt(payments[case.case_id]),
            }
            for case in cases
        ],
        "cases": [
            {
                "case_id": case.case_id,
                "buyer": case.buyer,
                "title": display_title(case.title),
                "status": case.status.value,
                "brief": brief(case),
                "resolved": reconciled(case),
                "balance": fmt(case.open_balance),
                "needs_approval": approval_count(case),
                "approved": approved_count(case),
                "submitted": len(case.receipts),
                "needs_attention": needs_attention(case),
                "tags": [{"label": label, "color": color} for label, color in case_tags(case)],
                "next_due": next_due_at(case).isoformat() if next_due_at(case) else None,
            }
            for case in cases
        ],
        "quarantined": wire(service.world.list_quarantined()),
    }


def case_data(service: Recoup, case_id: str) -> dict:
    case, history = service.world.view(case_id), service.history(case_id)
    priority = {"correction": 0, "dispute": 1, "info_request": 2, "credit_memo": 3}
    groups = sorted(
        proposal_groups(case, history).values(),
        key=lambda rows: (
            rows[-1].status not in {"proposed", "approved"},
            priority.get(rows[-1].kind.value, 4),
            rows[-1].business_key,
        ),
    )
    return {
        "brief": brief(case),
        "initial_balance": initial_balance(case, history),
        "decision_changes": decision_changes(case, history),
        "agent_runs": agent_runs(case, history),
        "policy_review": policy_review(history),
        "new_payments": fmt(new_payments(case, history)),
        "view": wire(case),
        "title": display_title(case.title),
        "balance": fmt(case.open_balance),
        "invoice_total": fmt(case.invoice_total),
        "money": money_table(case),
        "timeline": timeline_rows(history),
        "receipt_records": [
            {
                "receipt_id": receipt.receipt_id,
                "at": receipt.at.isoformat(),
                "label": receipt.label,
                "kind": next(
                    (
                        p.kind.value
                        for p in history.proposals_all
                        if p.proposal_id == receipt.proposal_id
                        and p.version == receipt.proposal_version
                    ),
                    "action",
                ),
                "amount": fmt(receipt.amount) if receipt.amount is not None else "No amount",
                "corrects": receipt.corrects_receipt_id,
                "version": receipt.proposal_version,
                "recipient": next(
                    (
                        p.recipient
                        for p in history.proposals_all
                        if p.proposal_id == receipt.proposal_id
                        and p.version == receipt.proposal_version
                    ),
                    "Recorded target",
                ),
                "draft_text": next(
                    (
                        p.draft_text
                        for p in history.proposals_all
                        if p.proposal_id == receipt.proposal_id
                        and p.version == receipt.proposal_version
                    ),
                    "Draft snapshot not available.",
                ),
                "citations": [
                    c.model_dump(mode="json")
                    for p in history.proposals_all
                    if p.proposal_id == receipt.proposal_id
                    and p.version == receipt.proposal_version
                    for c in p.citations
                ],
                "approvals": [
                    {"by": approval.approver, "at": approval.at.isoformat()}
                    for approval in history.approvals
                    if approval.proposal_id == receipt.proposal_id
                    and approval.proposal_version == receipt.proposal_version
                    and approval.approved
                ],
            }
            for receipt in history.receipts
        ],
        "ledger_records": [
            {
                "Date": entry.at.isoformat(),
                "Entry": entry.kind,
                "Line": entry.line_id or "Invoice",
                "Amount (USD)": fmt(entry.amount),
                "Reference": entry.source,
            }
            for entry in history.ledger
        ],
        "proposals": [
            {
                "current": wire(rows[-1]),
                "versions": wire(rows),
                "amount": fmt(rows[-1].amount) if rows[-1].amount is not None else "No amount",
                "allocations": [
                    {
                        "line_id": row.line_id,
                        "cents": str(row.amount.cents),
                        "amount": fmt(row.amount),
                    }
                    for row in rows[-1].allocations
                ],
            }
            for rows in groups
        ],
        "documents": [
            {
                "evidence": wire(row),
                "fields": evidence_fields(row, history),
                "source_facts": document_facts(row),
            }
            for row in evidence_versions(case, history)
        ],
    }


def mutate(service: Recoup, action: str, payload: dict) -> None:
    """Dispatch user intent without reimplementing service gates or amounts."""
    if action == "load":
        service.load([str(DEMO_ROOT / case_id) for case_id in ("H", "C", "N")])
    elif action == "advance":
        service.advance(days=payload.get("days"), to_next_due=payload.get("to_next_due", False))
    elif action == "run":
        case_id = payload.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("Open a case before running the agent.")
        service.run(case_id)
    elif action in {"edit", "approve", "reject", "submit"}:
        proposal_id, version = payload["proposal_id"], payload["version"]
        if not isinstance(proposal_id, str) or type(version) is not int or version < 1:
            raise ValueError("A proposal ID and exact integer version are required.")
        if action == "edit":
            changes = {key: payload[key] for key in ("draft_text", "recipient") if key in payload}
            if "allocations" in payload:
                allocations = []
                for row in payload["allocations"]:
                    cents = row["cents"]
                    if not isinstance(cents, str) or not re.fullmatch(r"[0-9]+", cents):
                        raise ValueError("Allocation cents must be non-negative integer text.")
                    allocations.append(
                        LineAmount(line_id=row["line_id"], amount=Money(cents=int(cents)))
                    )
                changes["allocations"] = allocations
            service.edit(proposal_id, version, **changes)
        elif action == "approve":
            service.approve(proposal_id, version)
        elif action == "submit":
            service.submit(proposal_id, version)
        else:
            reason = payload.get("reason", "").strip()
            if not reason:
                raise ValueError("A rejection reason is required.")
            service.reject(proposal_id, version, reason=reason)
    elif action == "confirm_field":
        service.confirm_field(payload["evidence_id"], payload["field"])
    elif action == "add_evidence":
        upload = payload.get("upload")
        inject_document(
            service,
            payload["case_id"],
            payload["document_json"],
            upload["name"] if upload else None,
            base64.b64decode(upload["base64"], validate=True) if upload else None,
        )
    else:
        raise ValueError(f"Unknown action: {action}")
