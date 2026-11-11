"""Reviewer guidance derived from actual snapshots and receipts (design/02 §6)."""

import json
from datetime import timedelta

from recoup.contracts.models import CaseHistory, CaseView, Proposal, Receipt
from recoup.contracts.money import Money, fmt

SCENARIO = "reviewer-v2"


def is_reviewer(cases: list[CaseView]) -> bool:
    return bool(cases) and all(
        any(e.active and e.fields.get("demo_scenario") == SCENARIO for e in c.evidence)
        for c in cases
    )


def kind_of(case: CaseView, receipt: Receipt) -> str:
    return next((p.kind.value for p in case.proposals if p.proposal_id == receipt.proposal_id), "")


def reconciled(case: CaseView) -> bool:
    return case.open_balance.cents == 0


def live_proposals(case: CaseView, kind: str, line: str | None = None) -> list[Proposal]:
    return [
        p
        for p in case.proposals
        if p.kind == kind
        and p.status in {"proposed", "approved"}
        and (line is None or any(a.line_id == line for a in p.allocations))
    ]


def posted(case: CaseView, kind: str, line: str | None = None) -> bool:
    return any(
        kind_of(case, r) == kind and (line is None or any(a.line_id == line for a in r.allocations))
        for r in case.receipts
    )


def journey(cases: list[CaseView]) -> dict | None:
    if not is_reviewer(cases) or {c.case_id for c in cases} != {"H", "C", "N"}:
        return None
    by_id = {c.case_id: c for c in cases}
    h, c, n = (by_id[key] for key in ("H", "C", "N"))
    statement = any(e.active and e.doc_ref == "STATEMENT" for e in n.evidence)
    rows = [
        (
            "credit-c",
            "Valid deduction: honor the agreed price",
            (
                "Harbor's signed amendment supports the $500 pricing deduction. "
                "Approve the credit we owe. This is correct accounting, not money "
                "saved."
            ),
            "C",
            "credit_memo",
            reconciled(c),
            "Review",
            "review",
        ),
        (
            "dispute-h",
            "Invalid deduction: protect $3,120",
            (
                "Northwind's signed POD records the full shipment. Dispute its "
                "unsupported $3,120 shortage deduction. No credit should be issued."
            ),
            "H",
            "dispute",
            posted(h, "dispute"),
            "Review",
            "review",
        ),
        (
            "credit-n",
            "Separate Juniper's valid credit from unpaid debt",
            (
                "Honor the $2,150 pricing deduction. The remaining $5,000 is still "
                "owed and needs a separate collection and insurance response."
            ),
            "N",
            "credit_memo",
            posted(n, "credit_memo"),
            "Review",
            "review",
        ),
        (
            "notice-n",
            "Check the policy and notify the insurer",
            (
                "Review the policy checks and net $5,000 ledger balance. Approve and "
                "submit the MOCK notice; its receipt starts the policy's three-day "
                "demonstration waiting period."
            ),
            "N",
            "insurer_notice",
            posted(n, "insurer_notice"),
            "Insurance",
            "review",
        ),
        (
            "wait-3",
            "Day 3: a buyer repayment and a claim window",
            (
                "Advance to the next event. Northwind sends its acknowledgment and "
                "$3,120 bank confirmation. Juniper's claim window opens, but its "
                "account statement is still missing."
            ),
            "N",
            None,
            h.sim_day >= 3,
            "Insurance",
            "advance",
        ),
        (
            "statement-5",
            "A missing document blocks claim submission",
            (
                "The claim draft is available, but the statement checklist item is "
                "missing. Inspect the checklist below; submission is blocked. Advance "
                "to day 5 for Finance's statement and automatic reassessment."
            ),
            "N",
            "claim_package",
            statement,
            "Insurance",
            "advance",
        ),
        (
            "claim-n",
            "Submit the ready claim package for review",
            (
                "The statement now confirms $5,000 remains unpaid after the valid "
                "credit. Review the refreshed package and policy citations, approve "
                "this version, then submit the MOCK claim. Submission is not an "
                "insurer decision or payment."
            ),
            "N",
            "claim_package",
            posted(n, "claim_package"),
            "Outcomes",
            "review",
        ),
    ]
    current = next((i for i, row in enumerate(rows) if not row[5]), len(rows))
    result = []
    for i, (key, title, description, cid, kind, done, phase, action) in enumerate(rows):
        candidates = live_proposals(by_id[cid], kind) if kind else []
        proposal = candidates[0] if candidates else None
        result.append(
            dict(
                id=key,
                title=title,
                description=description,
                case_id=cid,
                kind=kind,
                phase=phase,
                action=action,
                state="complete" if done else "current" if i == current else "upcoming",
                proposal_id=proposal.proposal_id if proposal else None,
                proposal_key=proposal.business_key if proposal else None,
                proposal_status=proposal.status.value if proposal else None,
                cta=f"Review {by_id[cid].buyer}" if action == "review" else "Advance to next event",
            )
        )
    return dict(
        title="Three cases, three outcomes",
        steps=result,
        completed=sum(row[5] for row in rows),
        total=len(rows),
        current=result[current] if current < len(result) else None,
        complete=current == len(rows),
        completion_title="A valid credit, a repaid dispute, and a submitted claim.",
        completion_summary=(
            "Harbor's valid deduction was credited. Northwind repaid $3,120 with "
            "no credit conceded. Juniper's $5,000 remains open with a MOCK claim "
            "submitted for insurer review. No insurer payment is recorded."
        ),
        out_of_order=(h.sim_day >= 3 and not posted(h, "dispute"))
        or (n.sim_day > 0 and not posted(n, "insurer_notice")),
        resolved=sum(reconciled(case) for case in cases),
        disclosure=(
            "Scripted offline agent simulation. Policy/tool checks and ledger "
            "changes are real service operations on synthetic data; this is not a "
            "live-model evaluation."
        ),
    )


def new_payments(case: CaseView, history: CaseHistory) -> Money:
    """Payments posted after this run's first investigation, from the actual ledger."""
    first = min(
        (t.sim_time for t in history.traces if t.kind == "model_call"), default=case.sim_now
    )
    return Money(
        cents=sum(e.amount.cents for e in history.ledger if e.kind == "payment" and e.at > first)
    )


def policy_review(history: CaseHistory) -> list[dict]:
    """Display recorded policy-tool answers, without interpreting policy prose in the UI."""
    answers = {}
    for trace in reversed(history.traces):
        if trace.tool != "check_policy" or not (trace.result or {}).get("ok"):
            continue
        for answer in trace.result["result"]["answers"]:
            key = (answer["question"], answer.get("clause_key"))
            if key in answers:
                continue
            value = answer.get("value")
            if answer["question"] == "credit_limit" and value is not None:
                value = fmt(Money(cents=int(value)))
            answers[key] = dict(
                question=answer["question"].replace("_", " "),
                clause_key=answer.get("clause_key"),
                result=answer.get("computed_date")
                or (
                    "Buyer and invoice date match"
                    if answer.get("applies") is True
                    else "Buyer or invoice date do not match"
                    if answer.get("applies") is False
                    else value or answer.get("note") or "Not established"
                ),
                basis=answer["basis"],
                citations=[answer["clause_citation"]] if answer.get("clause_citation") else [],
            )
    return list(reversed(list(answers.values())))


def brief(case: CaseView) -> dict:
    if posted(case, "claim_package"):
        return {
            "label": "MOCK claim submitted",
            "tone": "blue",
            "summary": (
                "The claim package has a MOCK receipt. The remaining debt is still "
                "open; submission records no insurer approval or payment."
            ),
        }
    if live_proposals(case, "claim_package"):
        ready = next(
            (r for r in reversed(case.readiness) if r.kind == "claim" and r.status != "stale"), None
        )
        return {
            "label": "Claim ready for review"
            if ready and ready.status == "ready"
            else "Claim needs documents",
            "tone": "orange",
            "summary": (
                "The agent checked the supplied policy and prepared a claim package. "
                "Review the document checklist; missing items block submission. The "
                "ledger balance is not a calculated insured loss."
            ),
        }
    if reconciled(case):
        repaid = any(e.active and e.doc_ref == "REPAYMENT" for e in case.evidence)
        return {
            "label": "Buyer repaid the deduction" if repaid else "Valid deduction credited",
            "tone": "green",
            ("summary"): (
                (
                    "The buyer acknowledgment and separate synthetic bank record confirm "
                    "repayment. No credit was conceded on the invalid deduction."
                )
                if repaid
                else (
                    "The supported buyer deduction was credited in the mock ledger. This "
                    "is a credit we owed, not money saved."
                )
            ),
        }
    if case.status == "needs_human":
        return {"label": "Human attention needed", "tone": "red", "summary": case.status_reason}
    if case.decision is None or any(line.verdict == "needs_info" for line in case.decision.lines):
        waiting = posted(case, "info_request")
        return {
            "label": "Waiting for buyer" if waiting else "Needs an explanation",
            "tone": "violet",
            "summary": "The deduction is not yet supported by enough evidence. "
            + (
                (
                    "An information request has been submitted; the agent will revisit "
                    "the case when a reply arrives."
                )
                if waiting
                else (
                    "Review the information request. The agent has not guessed a "
                    "deduction reason or amount."
                )
            ),
        }
    if live_proposals(case, "correction"):
        return {
            "label": "Earlier assessment changed",
            "tone": "orange",
            ("summary"): (
                "New source records changed the rule result. Review the correction "
                "linked to the earlier dispute, then apply any separately proposed "
                "credit."
            ),
        }
    if live_proposals(case, "credit_memo"):
        return {
            "label": "Credit ready for review",
            "tone": "orange",
            ("summary"): (
                "The current source records support a credit adjustment. Review the "
                "cited agreement or delivery record, then approve this exact draft "
                "before MOCK submission."
            ),
        }
    if posted(case, "insurer_notice"):
        return {
            "label": "Waiting for claim window",
            "tone": "blue",
            "summary": (
                "The MOCK notice receipt starts the waiting period in the supplied "
                "policy. The agent will prepare a claim package when the window opens; "
                "document readiness is checked separately."
            ),
        }
    if live_proposals(case, "insurer_notice"):
        return {
            "label": "Insurer notice ready",
            "tone": "orange",
            "summary": (
                "Review the supplied policy, overdue ledger balance, and insurer "
                "notice. Approval and MOCK submission are separate steps."
            ),
        }
    if posted(case, "dispute"):
        return {
            "label": "Awaiting buyer response",
            "tone": "blue",
            ("summary"): (
                "The unsupported buyer deduction has been disputed without issuing a "
                "credit. The agent will reassess when a buyer response or bank record "
                "arrives."
            ),
        }
    return {
        "label": "Review the proposed response",
        "tone": "orange",
        ("summary"): (
            "Compare the proposed action with its supporting documents. Each "
            "external MOCK action requires its own approval and submission."
        ),
    }


def initial_balance(case: CaseView, history: CaseHistory) -> str | None:
    for trace in history.traces:
        if trace.kind != "model_call" or not trace.request:
            continue
        for message in trace.request.get("messages", []):
            if message.get("role") == "user":
                try:
                    return fmt(
                        Money.model_validate(json.loads(message["content"])["case"]["open_balance"])
                    )
                except (KeyError, ValueError, TypeError):
                    continue
    return None


def decision_changes(case: CaseView, history: CaseHistory) -> list[dict]:
    if not case.decision:
        return []

    def signature(d):
        return [(line.line_id, line.verdict, line.valid, line.disputed) for line in d.lines]

    previous = next(
        (d for d in reversed(history.decisions) if signature(d) != signature(case.decision)), None
    )
    if previous is None:
        return []
    old = {line.line_id: line for line in previous.lines}
    return [
        {
            "line_id": line.line_id,
            "before": old[line.line_id].verdict.value.replace("_", " "),
            "after": line.verdict.value.replace("_", " "),
            "supported_before": fmt(old[line.line_id].valid)
            if old[line.line_id].valid is not None
            else "Not determined",
            "supported_after": fmt(line.valid) if line.valid is not None else "Not determined",
            "rationale": line.rationale,
            "citations": [c.model_dump(mode="json") for c in line.citations],
        }
        for line in case.decision.lines
        if line.line_id in old
        and (line.verdict, line.valid, line.disputed)
        != (old[line.line_id].verdict, old[line.line_id].valid, old[line.line_id].disputed)
    ]


TOOL_LABELS = {
    "list_evidence": "Listed available documents",
    "read_evidence": "Read a source document",
    "run_rules": "Applied the deduction rules",
    "propose_decision": "Recorded the assessment",
    "classify_line": "Classified the buyer’s deduction",
    "readiness": "Checked document readiness",
    "check_policy": "Checked the supplied policy",
    "draft_proposal": "Prepared a draft for review",
    "request_approval": "Requested human approval",
    "schedule_followup": "Scheduled follow-up",
    "end": "Completed this investigation",
}


def agent_runs(case: CaseView, history: CaseHistory) -> list[dict]:
    groups = {}
    titles = {e.evidence_id: e.title.removeprefix("SYNTHETIC — ") for e in history.evidence_all}
    start = case.sim_now.date() - timedelta(days=case.sim_day)
    for t in history.traces:
        if t.kind not in {"tool_call", "model_call", "budget"}:
            continue
        key = (t.run_id, t.sim_time.isoformat())
        group = groups.setdefault(
            key,
            {
                "at": t.sim_time.isoformat(),
                "day": (t.sim_time.date() - start).days,
                "model": t.model_id,
                "mode": t.llm_mode or "fake",
                "model_calls": 0,
                "tools": [],
                "outcome": "Review recorded",
            },
        )
        if t.kind == "model_call":
            group["model_calls"] += 1
        elif t.kind == "budget":
            group["outcome"] = "Needs human attention: " + t.result_summary
        elif t.kind == "tool_call":
            envelope = t.result or {}
            result = envelope.get("result") or {}
            item = {
                "tool": t.tool,
                "label": TOOL_LABELS.get(t.tool, str(t.tool).replace("_", " ")),
                "ok": bool(envelope.get("ok"))
                and result.get("accepted") is not False
                and result.get("queued") is not False,
            }
            if t.tool == "read_evidence":
                item["detail"] = titles.get(result.get("evidence_id"), "Source document")
                item["evidence_id"] = result.get("evidence_id")
            elif t.tool == "end":
                group["outcome"] = (
                    "Current work complete; waiting for approvals or new evidence"
                    if result.get("accepted")
                    else "Further work required"
                )
            elif t.tool == "draft_proposal":
                item["detail"] = (
                    (result.get("business_key") or "")
                    .removeprefix(case.case_id + ":")
                    .split(":")[0]
                    .replace("_", " ")
                )
            if not item["ok"]:
                item["detail"] = "; ".join(
                    i["message"] for i in envelope.get("issues", []) + result.get("issues", [])
                )
            group["tools"].append(item)
    for group in groups.values():
        unique = {}
        group["tool_calls"] = len(group["tools"])
        for tool in group["tools"]:
            key = (tool["tool"], tool.get("evidence_id"), tool.get("detail"), tool["ok"])
            if key in unique:
                unique[key]["occurrences"] += 1
            else:
                unique[key] = {**tool, "occurrences": 1}
        group["tools"] = list(unique.values())
    return list(reversed(list(groups.values())))[0:12]


def update_summary(before: list[CaseView], after: list[CaseView]) -> dict:
    old = {c.case_id: c for c in before}
    changes = []
    for c in after:
        prior = old.get(c.case_id)
        if prior is None:
            changes.append(
                {
                    "case_id": c.case_id,
                    "buyer": c.buyer,
                    "summary": "Case loaded and reviewed by the offline agent.",
                }
            )
            continue
        pieces = []
        if prior.open_balance != c.open_balance:
            pieces.append(f"Open balance: {fmt(prior.open_balance)} → {fmt(c.open_balance)}.")
        new_docs = [
            e.title.removeprefix("SYNTHETIC — ")
            for e in c.evidence
            if e.evidence_id not in {e.evidence_id for e in prior.evidence}
        ]
        if new_docs:
            pieces.append("New evidence: " + "; ".join(new_docs) + ".")
        new_receipts = [
            r.receipt_id
            for r in c.receipts
            if r.receipt_id not in {r.receipt_id for r in prior.receipts}
        ]
        if new_receipts:
            pieces.append("MOCK receipt: " + ", ".join(new_receipts) + ".")
        fresh = [
            p.kind.value.replace("_", " ")
            for p in c.proposals
            if (p.proposal_id, p.version)
            not in {(p.proposal_id, p.version) for p in prior.proposals}
            and p.status in {"proposed", "approved"}
        ]
        if fresh:
            pieces.append("New drafts: " + ", ".join(dict.fromkeys(fresh)) + ".")
        if pieces:
            changes.append({"case_id": c.case_id, "buyer": c.buyer, "summary": " ".join(pieces)})
    return {"title": "What just happened", "changes": changes}


def document_facts(evidence) -> list[dict]:
    """Readable source values; prices are formatted, never recomputed."""
    labels = {
        "tolerance_cents": "Tolerance",
        "follow_up_days": "Follow-up interval (days)",
        "authority_cents": "Authority threshold",
        "allowed_authority_roles": "Authorized roles",
        "invoice_no": "Invoice",
        "invoice_date": "Invoice date",
        "due_date": "Payment due",
        "total_cents": "Invoice amount",
        "paid_cents": "Recorded payment",
        "paid_date": "Payment date",
        "delivered_date": "Delivery date",
        "ship_date": "Ship date",
        "effective_date": "Effective date",
        "authorized_by": "Authorized by",
        "authority_role": "Authority role",
        "amends": "Amends",
        "signed": "Signed receiving record",
        "exception_note": "Receiving exception",
        "from": "From",
        "to": "To",
        "sent_date": "Sent",
        "report_date": "Inspection date",
        "damaged_qty": "Damaged cases",
        "policy_id": "Policy reference",
        "credit_limit_cents": "Policy credit limit",
        "period_start": "Policy period starts",
        "period_end": "Policy period ends",
        "mep_days_after_due": "Maximum extension after due date (days)",
        "notice_days_after_mep": "Notice interval after extension (days)",
        "waiting_days_after_notice": "Claim wait after notice (days)",
        "disputed_debt_clause": "Disputed debt clause",
    }
    facts = []
    for key, value in evidence.fields.items():
        if key == "demo_scenario" or key.startswith("line."):
            continue
        label = labels.get(key)
        if key.startswith("price."):
            label = "Agreed unit price · " + key.removeprefix("price.").removesuffix("_cents")
        elif key.startswith("promo.") and key.endswith("cap_cents"):
            label = "Promotion cap · " + key.split(".")[1]
        elif key.startswith("received."):
            label = "Cases received · " + key.split(".", 1)[1]
        elif key.startswith("refused."):
            label = "Cases refused · " + key.split(".", 1)[1]
        elif key.startswith("shipped."):
            label = "Cases shipped · " + key.split(".", 1)[1]
        elif key.startswith("covered_buyer."):
            label = "Listed buyer"
        elif key.startswith("claim_doc."):
            label = "Required claim document"
        elif key.startswith("clause."):
            label = "Policy clause · " + key.removeprefix("clause.").replace("_", " ")
        if not label:
            continue
        display = (
            fmt(Money(cents=value))
            if key.endswith("_cents") and type(value) is int
            else "Yes"
            if value is True
            else "No"
            if value is False
            else str(value)
        )
        facts.append(
            {
                "key": key,
                "label": label,
                "value": display,
                "trust": evidence.field_trust.get(key, "source"),
            }
        )
    if evidence.kind == "invoice":
        prefixes = sorted(
            {
                key.rsplit(".", 1)[0]
                for key in evidence.fields
                if key.startswith("line.") and key.endswith(".sku")
            }
        )
        for prefix in prefixes:
            fields = evidence.fields
            unit = fields.get(prefix + ".unit_price_cents")
            display = str(fields.get(prefix + ".qty", "")) + " cases"
            if type(unit) is int:
                display += " · " + fmt(Money(cents=unit)) + " per case"
            facts.append(
                {
                    "key": prefix + ".sku",
                    "label": str(
                        fields.get(prefix + ".description", fields.get(prefix + ".sku", prefix))
                    ),
                    "value": display,
                    "trust": evidence.field_trust.get(prefix + ".sku", "source"),
                }
            )
    return facts
