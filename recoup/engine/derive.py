"""Code-owned proposal derivation; design/02 §3.8, §5.4, §8.1."""

from hashlib import sha256
from uuid import uuid4

from recoup.contracts.interfaces import GateError, World
from recoup.contracts.models import (
    KIND_TARGET,
    Decision,
    GateIssue,
    LineAmount,
    Money,
    Proposal,
    ProposalKind,
    Receipt,
)
from recoup.contracts.oracle import (
    StaticClaimItemOut,
    StaticLineOut,
    StaticOutput,
    StaticProposalOut,
)
from recoup.engine import readiness


def receipt_kind(receipt: Receipt, case_id: str) -> str:
    prefix = f"{case_id}:"
    return (
        receipt.business_key[len(prefix) :].split(":", 1)[0]
        if receipt.business_key.startswith(prefix)
        else ""
    )


def allocations(receipt: Receipt) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in receipt.allocations:
        result[item.line_id] = result.get(item.line_id, 0) + item.amount.cents
    return result


def derive(world: World, case_id: str, line_ids: list[str] | None = None) -> list[Proposal]:
    view = world.view(case_id)
    decision = world.current_decision(case_id)
    if (
        decision is None
        or not decision.current
        or decision.evidence_set_hash != world.evidence_set_hash(case_id)
    ):
        raise GateError(
            [GateIssue(code="stale_decision", message="A current decision is required")]
        )
    selected = set(line_ids) if line_ids is not None else {line.line_id for line in decision.lines}
    if not selected <= {line.line_id for line in decision.lines}:
        raise GateError([GateIssue(code="unknown_line", message="Unknown decision line")])
    receipts = view.receipts
    credits: dict[str, int] = {}
    for entry in world.ledger(case_id):
        if entry.kind == "credit_posted" and entry.line_id:
            credits[entry.line_id] = credits.get(entry.line_id, 0) + entry.amount.cents
    groups: dict[tuple[str, str | None], dict[str, int]] = {}
    reasons = {line.line_id: line.reason for line in view.lines}
    for line in decision.lines:
        if line.line_id not in selected:
            continue
        lid = line.line_id
        if line.verdict == "needs_info":
            groups.setdefault(("info_request", None), {})[lid] = 0
            continue
        if line.valid is None or line.disputed is None:
            raise GateError(
                [GateIssue(code="invalid_decision", message="Decision money missing", line_id=lid)]
            )
        credit = line.valid.cents - credits.get(lid, 0)
        if credit < 0:
            raise GateError(
                [
                    GateIssue(
                        code="over_credited",
                        message="over-credited; reversal out of scope",
                        line_id=lid,
                    )
                ]
            )
        if credit:
            groups.setdefault(("credit_memo", None), {})[lid] = credit
        if reasons.get(lid) == "nonpayment":
            groups.setdefault(("follow_up", None), {})[lid] = 0
            continue
        originals = [
            r for r in receipts if receipt_kind(r, case_id) == "dispute" and lid in allocations(r)
        ]
        remaining = {}
        for receipt in originals:
            withdrawn = sum(
                allocations(r).get(lid, 0)
                for r in receipts
                if r.corrects_receipt_id == receipt.receipt_id
            )
            remaining[receipt.receipt_id] = allocations(receipt)[lid] - withdrawn
        net = sum(remaining.values())
        excess = net - line.disputed.cents
        if excess > 0:
            for receipt in sorted(originals, key=lambda r: (r.at, r.receipt_id), reverse=True):
                amount = min(excess, remaining[receipt.receipt_id])
                if amount > 0:
                    groups.setdefault(("correction", receipt.receipt_id), {})[lid] = amount
                    excess -= amount
                if not excess:
                    break
        elif excess < 0:
            groups.setdefault(("dispute", None), {})[lid] = -excess
    return [
        _proposal(world, decision, kind, amounts, ref, receipts)
        for (kind, ref), amounts in groups.items()
    ]


def _proposal(world, decision: Decision, kind, amounts, ref, receipts) -> Proposal:
    case_id = decision.case_id
    lines = "+".join(sorted(amounts))
    base = f"{case_id}:{kind}:{lines}"
    if kind == "correction":
        n = 1 + sum(r.corrects_receipt_id == ref for r in receipts)
        key = f"{case_id}:correction:{ref}:{n}"
    elif kind == "follow_up":
        key = f"{case_id}:follow_up:{1 + sum(receipt_kind(r, case_id) == kind for r in receipts)}"
    elif kind in {"credit_memo", "dispute"} and any(
        receipt_kind(r, case_id) == kind for r in receipts
    ):
        n = 1 + sum(r.business_key.startswith(base + ":inc:") for r in receipts)
        key = f"{base}:inc:{n}"
    else:
        key = base
    money = kind in {"credit_memo", "dispute", "correction"}
    return Proposal(
        proposal_id=str(uuid4()),
        business_key=key,
        version=1,
        case_id=case_id,
        kind=kind,
        target=KIND_TARGET[ProposalKind(kind)],
        recipient="",
        allocations=[
            LineAmount(line_id=lid, amount=Money(cents=value))
            for lid, value in sorted(amounts.items())
        ],
        amount=Money(cents=sum(amounts.values())) if money else None,
        draft_text="",
        draft_sha256=sha256(b"").hexdigest(),
        citations=[],
        decision_id=decision.decision_id,
        decision_version=decision.version,
        evidence_set_hash=decision.evidence_set_hash,
        corrects_receipt_id=ref,
        status="proposed",
        created_at=world.clock.now(),
        created_by="agent",
    )


def static_output(world: World, case_id: str) -> StaticOutput:
    view = world.view(case_id)
    facts = world.fact_set(case_id)
    from recoup.engine.rules import run_rules

    findings = run_rules(view.lines, facts, world.ledger(case_id))
    claim_items = []
    deadline = None
    if any(doc.kind == "insurance_policy" for doc in facts.docs):
        claim = readiness.claim(
            facts, world.ledger(case_id), view.receipts, world.clock.now().date()
        )
        claim_items = [StaticClaimItemOut(item_id=i.item_id, status=i.status) for i in claim.items]
        deadline = readiness.notice(
            facts, world.ledger(case_id), view.receipts, world.clock.now().date(), findings
        ).deadline
    decision = world.current_decision(case_id)
    lines = (
        decision.lines
        if decision and decision.current and decision.evidence_set_hash == facts.basis_hash
        else []
    )
    return StaticOutput(
        case_id=case_id,
        lines=[
            StaticLineOut(
                line_id=line.line_id,
                verdict=line.verdict,
                valid_cents=line.valid.cents if line.valid else None,
                disputed_cents=line.disputed.cents if line.disputed else None,
                citations=line.citations,
            )
            for line in lines
        ],
        proposals=[
            StaticProposalOut(
                kind=p.kind,
                line_ids=[a.line_id for a in p.allocations],
                amount_cents=p.amount.cents if p.amount else None,
            )
            for p in view.proposals
            if p.status in {"proposed", "approved", "submitted_mock"}
            and p.evidence_set_hash == facts.basis_hash
        ],
        missing={f.line_id: f.missing for f in findings if f.missing},
        notice_deadline=deadline,
        claim_items=claim_items,
    )
