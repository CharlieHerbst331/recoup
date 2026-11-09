"""Deduction intake from the vocabulary in design/02 §3.7."""

import re
from datetime import date

from recoup.contracts.models import (
    DeductionLine,
    DeductionReason,
    Evidence,
    FieldTrust,
    LedgerEntry,
    LineReasonRevision,
)
from recoup.contracts.money import Money

from .ledger import balance, cents


def deduction_lines(
    evidence: list[Evidence],
    ledger: list[LedgerEntry],
    now: date,
    reasons: list[LineReasonRevision],
) -> list[DeductionLine]:
    result: dict[str, DeductionLine] = {}
    tolerance = 0
    due_date = None
    for doc in evidence:
        if doc.kind == "company_policy":
            tolerance = cents(doc.fields, "tolerance_cents")
        if doc.kind == "invoice" and doc.fields.get("due_date"):
            due_date = date.fromisoformat(str(doc.fields["due_date"]))
        if doc.kind not in {"remittance", "debit_memo"}:
            continue
        indexes = sorted(
            {int(m[1]) for key in doc.fields if (m := re.fullmatch(r"ded\.(\d+)\.line_id", key))}
        )
        for index in indexes:
            prefix = f"ded.{index}."
            line_id = str(doc.fields[prefix + "line_id"])
            raw_reason = doc.fields.get(prefix + "reason")
            line = DeductionLine(
                line_id=line_id,
                reason=DeductionReason(raw_reason) if raw_reason is not None else None,
                claimed=Money(cents=doc.fields.get(prefix + "claimed_cents", 0)),
                sku=doc.fields.get(prefix + "sku"),
                qty=doc.fields.get(prefix + "qty"),
                buyer_ref=doc.fields.get(prefix + "ref"),
                source_evidence_id=doc.evidence_id,
                reason_trust=doc.field_trust.get(prefix + "reason", FieldTrust.source),
            )
            if line_id in result and result[line_id] != line:
                raise ValueError(f"Conflicting deduction line {line_id}")
            result[line_id] = line
    paid = sum(e.amount.cents for e in ledger if e.kind == "payment")
    has_payment = any(e.kind == "payment" for e in ledger)
    prior_sources = {doc.doc_ref for doc in evidence if doc.kind == "credit_memo"}
    intake_balance = sum(
        entry.amount.cents * (1 if entry.kind == "invoice" else -1)
        for entry in ledger
        if entry.kind != "credit_posted" or entry.source in prior_sources
    )
    gap = intake_balance - sum(line.claimed.cents for line in result.values())
    if (has_payment or result) and gap > tolerance:
        result["U1"] = DeductionLine(
            line_id="U1", reason=DeductionReason.unexplained_short_pay, claimed=Money(cents=gap)
        )
    elif (
        paid == 0
        and not result
        and due_date is not None
        and now > due_date
        and balance(ledger).cents > 0
    ):
        result["NP"] = DeductionLine(
            line_id="NP", reason=DeductionReason.nonpayment, claimed=balance(ledger)
        )
    for revision in reasons:
        if revision.line_id in result:
            result[revision.line_id] = result[revision.line_id].model_copy(
                update={"reason": revision.reason, "reason_trust": revision.trust}
            )
    return list(result.values())
