"""Pure readiness from design/02 §3.7 and §5.6."""

from datetime import date
from hashlib import sha256

from recoup.contracts.models import (
    Basis,
    DeductionLine,
    DocKind,
    FactSet,
    FieldTrust,
    LedgerEntry,
    Readiness,
    ReadinessItem,
    Receipt,
    RuleFinding,
    Verdict,
)
from recoup.contracts.money import Money

from . import policy


def _item(item_id, status, note="", citation=None, satisfied_by=()):
    return ReadinessItem(
        item_id=item_id,
        requirement=item_id,
        status=status,
        note=note,
        policy_citation=citation,
        satisfied_by=list(satisfied_by),
    )


def _balance(ledger):
    return Money(
        cents=sum(e.amount.cents if e.kind == "invoice" else -e.amount.cents for e in ledger)
    )


def _build(kind, facts, items, *, line_id=None, blocking=None, **kwargs):
    checked = items if blocking is None else [i for i in items if i.item_id in blocking]
    status = "ready" if checked and all(i.status == "present" for i in checked) else "not_ready"
    payload = f"{kind}:{facts.case_id}:{facts.basis_hash}:{line_id}:{items}:{kwargs}"
    return Readiness(
        readiness_id="R-" + sha256(payload.encode()).hexdigest(),
        case_id=facts.case_id,
        kind=kind,
        line_id=line_id,
        status=status,
        items=items,
        evidence_set_hash=facts.basis_hash,
        **kwargs,
    )


def dispute(line: DeductionLine, finding: RuleFinding, facts: FactSet) -> Readiness:
    if line.line_id != finding.line_id:
        raise ValueError("finding line mismatch")
    prefix = f"dispute.{line.line_id}."
    proven = (
        finding.basis == Basis.proven
        and finding.verdict in (Verdict.invalid, Verdict.partial)
        and finding.disputed is not None
        and finding.disputed.cents > 0
    )
    matching = [[f for f in facts.facts if f.citation == c] for c in finding.citations]
    trusted = all(
        rows and all(f.trust not in (FieldTrust.ocr, FieldTrust.vision) for f in rows)
        for rows in matching
    )
    # FactSet carries current effective citations, not raw Evidence/FactRevision (§3.7).
    current = all(
        rows
        and all(
            f.evidence_id in {d.evidence_id for d in facts.docs}
            and (not c.locator.startswith("fact:") or c.locator == f"fact:{f.fact_id}")
            for f in rows
        )
        for c, rows in zip(finding.citations, matching)
    )
    items = [
        _item(prefix + "finding", "present" if proven else "missing"),
        _item(prefix + "facts", "present" if trusted else "unknown"),
        _item(prefix + "citations", "present" if current else "unknown"),
        _item(prefix + "no_conflict", "present" if not finding.contradictions else "unknown"),
    ]
    return _build("dispute", facts, items, line_id=line.line_id)


def notice(
    facts: FactSet,
    ledger: list[LedgerEntry],
    receipts: list[Receipt],
    now: date,
    findings: list[RuleFinding] | None,
) -> Readiness:
    balance = _balance(ledger)
    applicability = policy.answer(facts, "applicability", None)[0]
    deadline = policy.answer(facts, "notice_deadline", None)[0]
    try:
        due = policy._date(policy._pick(facts, "invoice", "due_date"))
        trigger = "present" if balance.cents > 0 and now > due else "missing"
    except policy._Unavailable:
        trigger = "unknown"
    items = [
        _item(
            "notice.applicability",
            "present"
            if applicability.applies is True
            else "missing"
            if applicability.applies is False
            else "unknown",
            applicability.note,
            applicability.clause_citation,
        ),
        _item("notice.trigger", trigger),
        _item(
            "notice.deadline",
            "present" if deadline.computed_date else "unknown",
            deadline.note,
            deadline.clause_citation,
        ),
        _item("notice.balance_basis", "present" if ledger else "missing"),
    ]
    deductions = [f for f in findings or [] if f.rule_id != "nonpayment"]
    uncertain = [
        f for f in deductions if f.verdict == Verdict.needs_info or f.basis != Basis.proven
    ]
    disputed = [
        f
        for f in deductions
        if f.verdict in (Verdict.invalid, Verdict.partial) and f.basis == Basis.proven
    ]
    citation = None
    if findings is None or uncertain:
        status = "unknown"
        note = "; ".join(f"{f.line_id}: {', '.join(f.missing) or f.note}" for f in uncertain)
        note = note or "findings not computed"
    elif not disputed:
        status, note = "present", "no buyer dispute"
    else:
        try:
            clause = policy._policy(facts, "disputed_debt_clause")
            citation = clause.citation
            status = {
                "excluded_until_resolved": "restricted",
                "notice_still_required": "present",
            }.get(clause.value, "unknown")
        except policy._Unavailable:
            status = "unknown"
        notes = []
        for finding in disputed:
            sent = any(
                r.business_key.startswith(f"{facts.case_id}:dispute:")
                and any(a.line_id == finding.line_id for a in r.allocations)
                for r in receipts
            )
            notes.append(
                f"{finding.line_id}: " + ("submitted" if sent else "established, not submitted")
            )
        note = "; ".join(notes)
    items.append(_item("notice.dispute_status", status, note, citation))
    return _build(
        "notice",
        facts,
        items,
        blocking={i.item_id for i in items[:-1]},
        balance_basis=balance,
        deadline=deadline.computed_date,
        deadline_citation=deadline.clause_citation,
    )


def claim(
    facts: FactSet, ledger: list[LedgerEntry], receipts: list[Receipt], now: date
) -> Readiness:
    balance = _balance(ledger)
    receipt = policy._receipt(receipts, facts, "insurer_notice")
    window = policy.answer(facts, "claim_window", receipt)[0]
    items = [
        _item(
            "claim.notice_receipt",
            "present" if receipt else "missing",
            satisfied_by=[receipt.receipt_id] if receipt else [],
        ),
        _item(
            "claim.waiting_period",
            "unknown"
            if window.computed_date is None
            else "present"
            if now >= window.computed_date
            else "missing",
            window.note,
            window.clause_citation,
        ),
    ]
    documents = policy.answer(facts, "claim_documents", receipt)
    for document in documents:
        if document.basis != Basis.proven or document.value not in DocKind._value2member_map_:
            items.append(_item("claim.documents", "unknown", document.note))
            continue
        kind = document.value
        docs = [d for d in facts.docs if d.kind == kind]
        readable = [d for d in docs if d.readable]
        complete = [
            d
            for d in readable
            if kind != "pod"
            or any(
                f.evidence_id == d.evidence_id
                and f.key == "signed"
                and f.value is True
                and f.trust not in (FieldTrust.ocr, FieldTrust.vision)
                for f in facts.facts
            )
        ]
        status = "present" if complete else "defective" if docs else "missing"
        note = ""
        if docs and not readable:
            note = "; ".join(str(d.failure.value if d.failure else "unreadable") for d in docs)
        elif readable and not complete:
            note = "signed POD not established"
        items.append(
            _item(
                f"claim.doc.{kind}",
                status,
                note,
                document.clause_citation,
                [d.evidence_id for d in complete],
            )
        )
    followup = policy._receipt(receipts, facts, "follow_up")
    collection_docs = [
        d.evidence_id for d in facts.docs if d.kind == "collection_note" and d.readable
    ]
    history = ([followup.receipt_id] if followup else []) + collection_docs
    items.append(
        _item("claim.collection_history", "present" if history else "missing", satisfied_by=history)
    )
    try:
        clause = policy._policy(facts, "disputed_debt_clause")
        status = {"excluded_until_resolved": "restricted", "notice_still_required": "present"}.get(
            clause.value, "unknown"
        )
        items.append(_item("claim.disputed_portion", status, citation=clause.citation))
    except policy._Unavailable as exc:
        items.append(_item("claim.disputed_portion", "unknown", exc.note))
    limit = policy.answer(facts, "credit_limit", receipt)[0]
    items.append(
        _item(
            "claim.credit_limit",
            "unknown"
            if limit.value is None
            else "restricted"
            if balance.cents > int(limit.value)
            else "present",
            limit.note,
            limit.clause_citation,
        )
    )
    return _build("claim", facts, items, balance_basis=balance)
