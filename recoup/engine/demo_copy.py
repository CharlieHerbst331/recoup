"""Deterministic offline wording from existing facts and rule amounts (§5.9)."""

from recoup.contracts.models import CaseView, Proposal, Receipt
from recoup.contracts.money import Money, fmt


def _label(mode: str) -> str:
    return f"SYNTHETIC data. MOCK action. LLM {mode}.\n\n"


def invoice_reference(case: CaseView) -> str:
    return str(
        next(
            (
                e.fields["invoice_no"]
                for e in case.evidence
                if e.active and e.kind == "invoice" and e.fields.get("invoice_no")
            ),
            case.case_id,
        )
    )


def finding_explanation(finding: dict) -> str:
    reason = str(finding["rule_id"]).replace("_", " ")
    if finding["verdict"] == "needs_info":
        missing = ", ".join(finding.get("missing", [])) or str(finding["basis"]).replace("_", " ")
        return (
            f"The {reason} deduction cannot be resolved from the current records. "
            f"Needed: {missing}. No financial decision is inferred from missing "
            f"evidence."
        )
    valid = fmt(Money.model_validate(finding["valid"]))
    disputed = fmt(Money.model_validate(finding["disputed"]))
    if finding["rule_id"] == "nonpayment":
        return (
            f"The signed delivery record supports collecting the unpaid balance "
            f"of {disputed}. This is debt still owed, not a valid buyer deduction. "
            f"The insurer track separately checks the supplied policy and documents."
        )
    return (
        f"The {reason} review supports {valid} of this deduction; {disputed} "
        f"remains disputed. The amounts come from the rules using the cited "
        f"source records."
    )


def source_explanation(case: CaseView, proposal: Proposal) -> str:
    cited = {c.evidence_id for c in proposal.citations}
    notes = []
    for doc in case.evidence:
        if not doc.active or doc.evidence_id not in cited:
            continue
        fields = {
            key: value
            for key, value in doc.fields.items()
            if doc.field_trust.get(key, "source") in {"source", "human_confirmed"}
        }
        if doc.kind == "invoice":
            for key, sku in fields.items():
                if key.startswith("line.") and key.endswith(".sku"):
                    prefix = key.removesuffix(".sku")
                    unit = fields.get(prefix + ".unit_price_cents")
                    quantity = fields.get(prefix + ".qty")
                    if type(unit) is int and type(quantity) is int:
                        notes.append(
                            f"The invoice lists {quantity} cases of {sku} at "
                            f"{fmt(Money(cents=unit))} per case."
                        )
        elif doc.kind == "pod":
            for key, value in fields.items():
                if key.startswith("received.") and type(value) is int:
                    notes.append(
                        f"POD v{doc.version} records {value} cases received for "
                        f"{key.split('.', 1)[1]}."
                    )
                elif key.startswith("refused.") and type(value) is int:
                    notes.append(
                        f"The receiving record also lists {value} refused cases "
                        f"for {key.split('.', 1)[1]}."
                    )
        if doc.kind in {"amendment", "email", "contract"}:
            for key, value in fields.items():
                if key.startswith("price.") and key.endswith("_cents") and type(value) is int:
                    subject = (
                        "The amendment lists" if "amends" in fields else "The original terms list"
                    )
                    notes.append(f"{subject} {key[6:-6]} at {fmt(Money(cents=value))} per case.")
                if key.startswith("promo.") and key.endswith("cap_cents") and type(value) is int:
                    subject = (
                        "The signed amendment records"
                        if "amends" in fields
                        else "The original terms record"
                    )
                    notes.append(
                        f"{subject} a {key.split('.')[1]} rebate cap of {fmt(Money(cents=value))}."
                    )
            if fields.get("amends") and fields.get("authorized_by"):
                notes.append(
                    f"The amendment is attributed to {fields['authorized_by']} "
                    f"({fields.get('authority_role', 'recorded officer')}), effective "
                    f"{fields.get('effective_date', 'as recorded')}."
                )
    return "\n\nSource facts: " + " ".join(notes[:8]) if notes else ""


def proposal_text(case: CaseView, proposal: Proposal, mode: str) -> str:
    invoice = invoice_reference(case)
    amount = fmt(proposal.amount) if proposal.amount is not None else None
    lines = {line.line_id: line for line in case.lines}
    decisions = {line.line_id: line for line in case.decision.lines} if case.decision else {}
    summary = []
    for row in proposal.allocations:
        line = lines.get(row.line_id)
        reason = line.reason.value.replace("_", " ") if line and line.reason else "deduction"
        summary.append(f"- {row.line_id}, {reason}: {fmt(row.amount)}.")
    sources = {e.evidence_id: e.title.removeprefix("SYNTHETIC — ") for e in case.evidence}
    cited = list(
        dict.fromkeys(sources.get(c.evidence_id, c.evidence_id) for c in proposal.citations)
    )
    source_note = "\n\nSupporting records: " + "; ".join(cited) + "." if cited else ""
    if proposal.kind == "credit_memo":
        body = (
            f"Subject: Credit adjustment for {case.buyer} — {invoice}\n\nPlease "
            f"post a {amount} credit against {invoice} for the supported portion "
            f"of the buyer’s deductions:\n"
        ) + "\n".join(summary)
        body += (
            "\n\nThe current source records support this adjustment. This "
            "request changes the receivable balance only; it does not record a "
            "cash payment."
        )
    elif proposal.kind == "dispute":
        body = (
            f"Subject: Deduction review request — {invoice}\n\nHello {case.buyer} "
            f"deductions team,\n\nPlease review the {amount} in deductions on "
            f"{invoice} that remain unsupported by the records currently "
            f"available:\n"
        ) + "\n".join(summary)
        body += (
            "\n\nPlease send any receiving exceptions, amended commercial terms, "
            "or other records that explain these amounts. We will revisit the "
            "assessment when new evidence arrives."
        )
        for row in proposal.allocations:
            decision = decisions.get(row.line_id)
            if decision:
                body += f"\n\nCurrent assessment for {row.line_id}: {decision.rationale}"
    elif proposal.kind == "correction":
        body = (
            f"Subject: Correction to {proposal.corrects_receipt_id} — "
            f"{invoice}\n\nHello {case.buyer} deductions team,\n\nNew evidence "
            f"changes our earlier assessment. Please withdraw {amount} from the "
            f"prior dispute referenced above for:\n"
        ) + "\n".join(summary)
        body += (
            "\n\nThe revised source records now support these deductions. Please "
            "retain this correction with the original correspondence. Any credit "
            "adjustment is a separate approval and MOCK accounting action."
        )
    elif proposal.kind == "info_request":
        body = (
            f"Subject: Please explain the short payment on {invoice}\n\nHello "
            f"{case.buyer} accounts payable team,\n\nOur records show an open "
            f"difference of {fmt(case.open_balance)} on {invoice}. We need more "
            f"information before deciding whether a credit or dispute is "
            f"appropriate.\n\nPlease send the remittance detail, affected invoice "
            f"line references, deduction reasons, and supporting agreement or "
            f"receiving records. We will review the response against the original "
            f"invoice and sales terms."
        )
    elif proposal.kind == "follow_up":
        last = max(case.receipts, key=lambda r: r.at, default=None)
        return followup_text(case, last, mode)
    elif proposal.kind == "counteroffer":
        body = (
            f"Subject: Conditional offer for review — {invoice}\n\nConditional "
            f"MOCK offer for {amount}, reference {proposal.offer_ref}.\n"
        ) + "\n".join(summary)
        body += (
            "\nThis is a proposal for review and does not record acceptance, "
            "settlement, or payment."
        )
    else:
        return insurance_text(case.model_dump(mode="json"), proposal.kind.value, invoice, mode)
    return _label(mode) + body + source_explanation(case, proposal) + source_note


def followup_text(case: CaseView, receipt: Receipt | None, mode: str) -> str:
    reference = receipt.receipt_id if receipt else "our previous correspondence"
    return _label(mode) + (
        f"Subject: Follow-up on {invoice_reference(case)}\n\nHello "
        f"{case.buyer} accounts payable team,\n\nWe are following up on "
        f"{reference}. The current open balance is {fmt(case.open_balance)}. "
        f"Please confirm the status of the deduction review and provide any "
        f"missing supporting records. No later buyer response is recorded in "
        f"this case."
    )


def insurance_text(
    case: dict, kind: str, invoice: str, mode: str = "fake", *, policy_answers: list | None = None
) -> str:
    balance = fmt(Money.model_validate(case["open_balance"]))
    label = "overdue-account notice" if kind == "insurer_notice" else "claim document package"
    body = (
        f"Subject: {case['buyer']} — {invoice} — {label} for review\n\nPlease "
        f"review the attached case records. The current receivable balance is "
        f"{balance}. This is the ledger balance after recorded payments and "
        f"credits, not a calculated insured loss. This MOCK {label} requests "
        f"insurer review of the remaining unpaid debt. Credited buyer deductions "
        f"are not added back to that balance."
    )
    reviewed = []
    for answer in policy_answers or []:
        question, value = answer["question"], answer.get("value")
        if answer.get("computed_date"):
            reviewed.append(f"- {question.replace('_', ' ')}: {answer['computed_date']}.")
        elif question == "applicability" and answer.get("applies") is not None:
            reviewed.append(
                "- Buyer and invoice date match the supplied policy list: "
                + ("yes." if answer["applies"] else "no.")
            )
        elif question == "credit_limit" and value is not None:
            reviewed.append(f"- Policy credit limit: {fmt(Money(cents=int(value)))}.")
        elif question == "claim_documents" and value:
            reviewed.append(f"- Required document: {value.replace('_', ' ')}.")
        elif question in {"exclusions", "disputed_debt"} and value:
            reviewed.append(f'- Supplied policy wording ({question.replace("_", " ")}): "{value}"')
    if reviewed:
        body += "\n\nRecorded policy checks:\n" + "\n".join(reviewed)
    if kind == "claim_package":
        readiness = next(
            (
                r
                for r in reversed(case["readiness"])
                if r["kind"] == "claim" and r["status"] != "stale"
            ),
            None,
        )
        gaps = (
            [
                item["requirement"]
                for item in readiness["items"]
                if item["status"] in {"missing", "unknown", "defective", "restricted"}
            ]
            if readiness
            else ["a current document checklist"]
        )
        if gaps:
            body += (
                "\n\nChecklist items still requiring attention: "
                + ", ".join(gaps)
                + ". Submission remains subject to the service checks."
            )
        else:
            body += "\n\nThe current document checklist is ready for MOCK submission."
    body += (
        "\n\nThis does not establish coverage or eligibility. "
        "This does not establish payout or claim approval. "
        "This does not guarantee recovery."
    )
    return _label(mode) + body
