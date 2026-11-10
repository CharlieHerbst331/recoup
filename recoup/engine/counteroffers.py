"""Counteroffer consumers; design/02 §3.7–3.8 and §5.4–5.5."""

from datetime import date
from urllib.parse import quote

from recoup.contracts.interfaces import GateError
from recoup.contracts.models import GateIssue, LineAmount
from recoup.contracts.money import Money
from recoup.engine.rules import NeedsHumanError


def _fail(code, message):
    raise GateError([GateIssue(code=code, message=message)])


def derive_counteroffer(world, case_id, line_ids, offer_ref, *, edited=None):
    from recoup.engine.derive import _proposal, receipt_kind

    facts = world.fact_set(case_id)
    view = world.view(case_id)
    decision = world.current_decision(case_id)
    if not decision or not decision.current or decision.evidence_set_hash != facts.basis_hash:
        _fail("stale_decision", "A current decision is required")
    if not offer_ref or not line_ids or len(set(line_ids)) != len(line_ids):
        _fail("invalid_counteroffer", "Select an offer and distinct deduction lines")
    receipts = [r for r in view.receipts if receipt_kind(r, case_id) == "counteroffer"]
    if any(r.offer_ref == offer_ref for r in receipts):
        _fail("offer_already_submitted", "Offer reference has already been submitted")
    citations = []

    def value(items, key, *, money=False):
        found = [f for f in items if f.key == key]
        if not found or any(
            type(f.value) is not type(found[0].value) or f.value != found[0].value for f in found
        ):
            _fail("invalid_offer_source", f"Missing or conflicting {key}")
        for fact in found:
            world.resolve_citation(fact.citation, facts.basis_hash)
            if money and fact.trust not in {"source", "human_confirmed"}:
                _fail("untrusted_offer", "Offer money requires source or human confirmation")
            if fact.citation not in citations:
                citations.append(fact.citation)
        result = found[0].value
        if money and (type(result) is not int or result < 0):
            _fail("counteroffer_amount", "Offer money must be a nonnegative integer")
        return result

    authority = value(
        [f for f in facts.facts if f.doc_kind == "company_policy"], "authority_cents", money=True
    )
    prefix = f"offer.{offer_ref}."
    emails = {
        f.evidence_id for f in facts.facts if f.doc_kind == "email" and f.key.startswith(prefix)
    }
    if not emails:
        _fail("invalid_offer_source", "No active selected offer")
    amounts = {}
    expiries = []
    senders = []
    for evidence_id in sorted(emails):
        items = [f for f in facts.facts if f.evidence_id == evidence_id]
        sender = value(items, "from")
        if sender not in facts.buyer_senders:
            _fail("invalid_offer_source", "Offer sender is not an allowed buyer")
        senders.append(sender)
        expiry = value(items, prefix + "expires_date")
        try:
            if type(expiry) is not str or date.fromisoformat(expiry).isoformat() != expiry:
                raise ValueError
            expired = date.fromisoformat(expiry) < world.clock.now().date()
        except (ValueError, TypeError):
            _fail("invalid_offer_source", "Offer expiry must be an ISO date")
        expiries.append(expiry)
        if expired:
            _fail("expired_offer", "Selected offer has expired")
        for lid in line_ids:
            amount = value(items, f"{prefix}line.{lid}.concession_cents", money=True)
            if amount <= 0 or (lid in amounts and amounts[lid] != amount):
                _fail("counteroffer_amount", "Offer concessions must be positive and consistent")
            amounts[lid] = amount
    if len(set(expiries)) != 1:
        _fail("invalid_offer_source", "Conflicting offer expiry")
    if len(set(senders)) != 1:
        _fail("invalid_offer_source", "Conflicting offer sender")
    used = sum(r.amount.cents for r in receipts if r.amount)
    spent = {}
    for receipt in receipts:
        for allocation in receipt.allocations:
            spent[allocation.line_id] = spent.get(allocation.line_id, 0) + allocation.amount.cents
    decisions = {line.line_id: line for line in decision.lines}
    actual_lines = {line.line_id: line for line in view.lines}
    if used > authority or any(
        lid not in decisions
        or decisions[lid].disputed is None
        or amount > decisions[lid].disputed.cents
        for lid, amount in spent.items()
    ):
        raise NeedsHumanError(
            "Past counteroffer receipts exceed current authority or line capacity"
        )
    actual = amounts if edited is None else edited
    if set(actual) != set(amounts) or any(
        type(v) is not int or v < 0 or v > amounts[lid] for lid, v in actual.items()
    ):
        _fail(
            "counteroffer_lines", "Edited allocations must retain selected lines and only decrease"
        )
    for lid, amount in actual.items():
        line = decisions.get(lid)
        if (
            lid not in actual_lines
            or actual_lines[lid].reason == "nonpayment"
            or not line
            or line.basis != "proven"
            or line.verdict not in {"invalid", "partial"}
            or not line.disputed
            or line.disputed.cents <= 0
        ):
            _fail("counteroffer_disputed", "Only proven disputed deductions can negotiate")
        if amount > line.disputed.cents - spent.get(lid, 0):
            _fail("counteroffer_disputed", "Offer exceeds remaining line capacity")
    total = sum(actual.values())
    if total <= 0:
        _fail("counteroffer_amount", "Offer aggregate must be positive")
    if total > authority - used:
        _fail("counteroffer_authority", "Offer exceeds remaining case authority")
    if total > world.ledger_balance(case_id).cents:
        _fail("counteroffer_balance", "Offer exceeds open balance")
    proposal = _proposal(world, decision, "counteroffer", actual, None, view.receipts)
    selector = quote(offer_ref, safe="")
    return proposal.model_copy(
        update=dict(
            business_key=f"{case_id}:counteroffer:{'+'.join(sorted(line_ids))}:offer:{selector}",
            offer_ref=offer_ref,
            amount=Money(cents=total),
            allocations=[
                LineAmount(line_id=lid, amount=Money(cents=actual[lid])) for lid in sorted(actual)
            ],
            citations=citations,
        )
    )


def available_counteroffers(world, case_id):
    facts = world.fact_set(case_id)
    from recoup.engine.derive import receipt_kind

    receipts = [
        r for r in world.view(case_id).receipts if receipt_kind(r, case_id) == "counteroffer"
    ]
    if receipts:
        authorities = [
            f for f in facts.facts if f.doc_kind == "company_policy" and f.key == "authority_cents"
        ]
        if authorities and all(
            type(f.value) is int
            and f.value >= 0
            and f.trust in {"source", "human_confirmed"}
            and f.value == authorities[0].value
            for f in authorities
        ):
            for fact in authorities:
                world.resolve_citation(fact.citation, facts.basis_hash)
            if sum(r.amount.cents for r in receipts if r.amount) > authorities[0].value:
                raise NeedsHumanError("Past counteroffer receipts exceed current authority")
        decision = world.current_decision(case_id)
        lines = {line.line_id: line for line in decision.lines} if decision else {}
        spent = {}
        for receipt in receipts:
            for allocation in receipt.allocations:
                spent[allocation.line_id] = (
                    spent.get(allocation.line_id, 0) + allocation.amount.cents
                )
        if any(
            lid not in lines or lines[lid].disputed is None or amount > lines[lid].disputed.cents
            for lid, amount in spent.items()
        ):
            raise NeedsHumanError("Past counteroffer receipts exceed current line capacity")
    refs = {
        f.key[len("offer.") : -len(".expires_date")]
        for f in facts.facts
        if f.doc_kind == "email" and f.key.startswith("offer.") and f.key.endswith(".expires_date")
    }
    result = []
    for ref in sorted(refs):
        ids = [
            line.line_id
            for line in world.view(case_id).lines
            if any(
                f.doc_kind == "email"
                and f.key == f"offer.{ref}.line.{line.line_id}.concession_cents"
                for f in facts.facts
            )
        ]
        try:
            result.append(derive_counteroffer(world, case_id, ids, ref))
        except GateError:
            continue
    return result
