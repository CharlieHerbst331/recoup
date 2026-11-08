"""Proposal validation at every World gate; design/02 §5.5."""

import re
from hashlib import sha256
from typing import Literal

from recoup.contracts.interfaces import GateError, World
from recoup.contracts.models import KIND_TARGET, GateIssue, Proposal
from recoup.engine import readiness
from recoup.engine.derive import derive
from recoup.engine.rules import run_rules


def assertion_issues(text: str, citations) -> list[GateIssue]:
    def quoted(match):
        quote = " ".join(match.group(1).split())
        return (
            ""
            if quote and any(quote in " ".join(c.quote.split()) for c in citations)
            else match.group(1)
        )

    text = re.sub(r'["“]([^"”]+)["”]', quoted, text)
    risky = (
        r"\b(coverage|covered|eligible|eligibility|payout|claim\s+(?:is\s+)?approv\w*"
        r"|recover\w*|guarantee\w*)\b"
    )
    scope_words = (
        r"be|been|being|currently|yet|necessarily|automatically|establish\w*|confirm\w*"
        r"|guarantee\w*|assert\w*|affirm\w*|assur\w*|promise\w*|determine\w*|mean|imply"
        r"|provide|constitute|covered|eligible|approv\w*|recover\w*|receiv\w*|entitled"
        r"|to|any|the|insurance|claim|of|or|and|coverage|eligibility|payout"
    )
    negated_before = (
        r"\b(?:no|not|never|cannot|can't|without|neither|isn't|aren't|doesn't|don't|won't)"
        r"\s+(?:(?:" + scope_words + r")\s+)*$"
    )
    negated_after = (
        r"^\s+(?:(?:is|are|does|do|has|will|would|can|could)\s+)?(?:not|never|cannot|can't)\b"
    )
    neutral_before = (
        r"\b(?:review|reviewing|request|requesting|assess|assessing|evaluate|evaluating"
        r"|questions? about|check|discuss|discussing)(?:\s+(?:a|the|review|of))*\s+$"
    )
    affirmative_after = (
        r"\b(?:confirmed|established|guaranteed|approved|assured|certain|will|is|are)\b"
    )
    for clause in re.split(
        r"[.!?;\n]|\b(?:but|however|yet)\b|\band\s+(?=(?:you|we|they|the|this|coverage|eligibility|payout|recovery)\b)",
        text,
        flags=re.I,
    ):
        for match in re.finditer(risky, clause, re.I):
            before, after = clause[: match.start()], clause[match.end() :]
            if re.search(negated_before, before, re.I) or re.search(negated_after, after, re.I):
                continue
            if re.search(neutral_before, before, re.I) and not re.search(
                affirmative_after, after, re.I
            ):
                continue
            return [
                GateIssue(
                    code="affirmative_assertion",
                    message="Draft affirms an insurance or recovery outcome",
                )
            ]
    return []


class ProposalValidator:
    def validate(
        self, world: World, proposal: Proposal, stage: Literal["save", "approve", "submit"]
    ) -> list[GateIssue]:
        issues: list[GateIssue] = []

        def issue(code, message, line_id=None):
            issues.append(GateIssue(code=code, message=message, line_id=line_id))

        case_id = proposal.case_id
        facts = world.fact_set(case_id)
        view = world.view(case_id)
        decision = world.current_decision(case_id)
        if proposal.target != KIND_TARGET[proposal.kind]:
            issue("wrong_target", "Proposal kind and target disagree")
        if proposal.recipient not in world.allowed_recipients(case_id, proposal.target):
            issue("invalid_recipient", "Recipient is not allowed for this case and target")
        if proposal.evidence_set_hash != facts.basis_hash:
            issue("stale_basis", "Evidence basis is no longer current")
        if (
            decision is None
            or not decision.current
            or decision.evidence_set_hash != facts.basis_hash
            or (proposal.decision_id, proposal.decision_version)
            != (decision.decision_id, decision.version)
        ):
            issue("stale_decision", "Proposal must use the current decision")
        if proposal.draft_sha256 != sha256(proposal.draft_text.encode()).hexdigest():
            issue("draft_hash_mismatch", "Draft hash does not match text")
        for citation in proposal.citations:
            try:
                evidence = world.evidence(citation.evidence_id)
                if evidence.case_id != case_id:
                    issue("case_scope", "Citation belongs to another case")
                    continue
                world.resolve_citation(citation, facts.basis_hash)
            except GateError as exc:
                issues.extend(exc.issues)
        relevant = [f for f in facts.facts if f.citation in proposal.citations]
        for fact in relevant:
            if fact.key.endswith(("_cents", "_bp")) and fact.trust in {"ocr", "vision"}:
                issue("untrusted_money", "Money facts require human confirmation")
        issues.extend(assertion_issues(proposal.draft_text, proposal.citations))
        ids = [a.line_id for a in proposal.allocations]
        if len(ids) != len(set(ids)):
            issue("duplicate_allocation", "Each line may be allocated once")
        if any(a.amount.cents < 0 for a in proposal.allocations):
            issue("invalid_allocation", "Allocations cannot be negative")
        if proposal.kind in {"credit_memo", "dispute", "correction", "info_request", "follow_up"}:
            try:
                candidates = derive(world, case_id, ids)
                expected = next(
                    (
                        p
                        for p in candidates
                        if p.kind == proposal.kind
                        and p.corrects_receipt_id == proposal.corrects_receipt_id
                    ),
                    None,
                )
                if expected is None or expected.business_key != proposal.business_key:
                    issue("unsupported_proposal", "No matching current derivation")
                else:
                    limits = {a.line_id: a.amount.cents for a in expected.allocations}
                    actual = {a.line_id: a.amount.cents for a in proposal.allocations}
                    if set(actual) != set(limits) or any(
                        value != limits[lid]
                        if proposal.created_by != "human_edit"
                        else value > limits[lid]
                        for lid, value in actual.items()
                        if lid in limits
                    ):
                        issue(
                            "unsupported_allocation",
                            "Allocations exceed or disagree with derivation",
                        )
                if proposal.kind in {"credit_memo", "dispute", "correction"}:
                    if proposal.amount is None or proposal.amount.cents != sum(
                        a.amount.cents for a in proposal.allocations
                    ):
                        issue("amount_mismatch", "Amount must equal allocations")
                elif proposal.amount is not None or any(
                    a.amount.cents for a in proposal.allocations
                ):
                    issue("amount_not_allowed", "This proposal has no monetary allocation")
            except GateError as exc:
                issues.extend(exc.issues)
        elif proposal.kind in {"insurer_notice", "claim_package"}:
            if proposal.business_key != f"{case_id}:{proposal.kind.value}:case":
                issue("invalid_business_key", "Invalid insurance proposal identity")
            if proposal.amount is not None or proposal.allocations:
                issue(
                    "amount_not_allowed",
                    "Insurance packages show a ledger balance, not a loss amount",
                )
        else:
            issue("unsupported_proposal", "Counteroffers are outside this implementation step")
        findings = run_rules(view.lines, facts, world.ledger(case_id))
        if proposal.kind in {"credit_memo", "dispute", "correction"}:
            for lid in ids:
                finding = next((f for f in findings if f.line_id == lid), None)
                decided = (
                    next((item for item in decision.lines if item.line_id == lid), None)
                    if decision
                    else None
                )
                if (
                    finding is None
                    or decided is None
                    or (decided.verdict, decided.basis, decided.valid, decided.disputed)
                    != (finding.verdict, finding.basis, finding.valid, finding.disputed)
                ):
                    issue(
                        "decision_rule_mismatch",
                        "Current rules do not support decision amounts",
                        lid,
                    )
                if finding:
                    for citation in finding.citations:
                        try:
                            world.resolve_citation(citation, facts.basis_hash)
                        except GateError as exc:
                            issues.extend(exc.issues)
        if proposal.kind == "dispute":
            for lid in ids:
                line = next((line for line in view.lines if line.line_id == lid), None)
                finding = next((f for f in findings if f.line_id == lid), None)
                if (
                    line is None
                    or finding is None
                    or readiness.dispute(line, finding, facts).status != "ready"
                ):
                    issue("dispute_not_ready", "Dispute line is not ready", lid)
        if (
            proposal.kind == "credit_memo"
            and proposal.amount
            and proposal.amount.cents > world.ledger_balance(case_id).cents
        ):
            issue("excess_credit", "Credit exceeds open balance")
        if proposal.kind in {"insurer_notice", "claim_package"}:
            kind = "notice" if proposal.kind == "insurer_notice" else "claim"
            saved = [
                r
                for r in world.readiness(case_id)
                if r.kind == kind
                and r.evidence_set_hash == facts.basis_hash
                and r.status != "stale"
            ]
            if not saved:
                issue("readiness_required", "Current readiness must be computed")
            if kind == "notice":
                current = readiness.notice(
                    facts, world.ledger(case_id), view.receipts, world.clock.now().date(), findings
                )
                if current.status != "ready":
                    issue("notice_not_ready", "Notice is not ready")
                if proposal.balance_basis != world.ledger_balance(case_id):
                    issue("stale_balance", "Notice balance differs from ledger")
            else:
                current = readiness.claim(
                    facts, world.ledger(case_id), view.receipts, world.clock.now().date()
                )
                if stage == "submit" and current.status != "ready":
                    issue("claim_not_ready", "Claim checklist is incomplete")
        return issues
