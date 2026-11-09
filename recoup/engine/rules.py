"""Pure rules from design/02 §3.7 and §5.3."""

import re
from datetime import date, timedelta

from recoup.contracts.models import (
    Basis,
    DeductionLine,
    DeductionReason,
    FactSet,
    FieldTrust,
    LedgerEntry,
    ProposalKind,
    RuleFinding,
    Verdict,
)
from recoup.contracts.money import Money, bp_of, clamp


class NeedsHumanError(ValueError):
    """Abort rule evaluation for a case requiring human interpretation."""


def require_legal_authority(facts: FactSet) -> None:
    """Called by the consumer when legal interpretation is required (§5.3)."""
    docs = [d for d in facts.docs if d.kind == "legal_authority"]
    if not any(d.readable for d in docs):
        raise NeedsHumanError(
            "legal authority unreadable" if docs else "legal authority not supplied"
        )


def proposal_kind(line: DeductionLine, finding: RuleFinding) -> ProposalKind | None:
    """Select the rule's action family; proposal construction belongs to §5.4."""
    if finding.line_id != line.line_id:
        raise ValueError("finding line mismatch")
    if finding.verdict == Verdict.needs_info:
        return ProposalKind.info_request
    if line.claimed.cents == 0:
        return None
    if line.reason == "nonpayment":
        return ProposalKind.follow_up
    return ProposalKind.dispute if finding.disputed.cents else ProposalKind.credit_memo


class _Undecidable(Exception):
    def __init__(self, basis, missing=(), contradictions=()):
        self.basis = basis
        self.missing = list(missing)
        self.contradictions = list(contradictions)


class _Inputs:
    def __init__(self, facts):
        self.facts = facts.model_copy(
            update={"facts": sorted(facts.facts, key=lambda f: (f.evidence_id, f.key))}
        )
        self.used = []
        self.flags = []
        self.terms = []

    def pick(self, rows, key, default=None, optional=False):
        rows = [f for f in rows if f.key == key]
        if not rows:
            if optional:
                return default
            raise _Undecidable(Basis.missing_evidence, [key])
        self.used.extend(f.citation for f in rows if f.citation not in self.used)
        if any(f.trust in (FieldTrust.ocr, FieldTrust.vision) for f in rows):
            raise _Undecidable(Basis.untrusted_facts, [key])
        if any(f.value != rows[0].value for f in rows[1:]):
            raise _Undecidable(
                Basis.contradiction,
                contradictions=[
                    (rows[0].citation, f.citation) for f in rows[1:] if f.value != rows[0].value
                ],
            )
        if rows[0].value is None:
            raise _Undecidable(Basis.missing_evidence, [key])
        return rows[0].value

    def get(self, kind, key, **kwargs):
        return self.pick([f for f in self.facts.facts if f.doc_kind == kind], key, **kwargs)

    def term(self, key, **kwargs):
        return self.pick(self.terms, key, **kwargs)

    def _contract(self):
        base = [f for f in self.facts.facts if f.doc_kind == "contract"]
        groups = {}
        for f in self.facts.facts:
            if f.doc_kind in ("amendment", "email"):
                groups.setdefault(f.evidence_id, []).append(f)
        amendments = []
        for rows in groups.values():
            if not any(f.key == "amends" for f in rows):
                continue
            author = self.pick(rows, "authorized_by", optional=True)
            role = self.pick(rows, "authority_role", optional=True)
            roles = self.get("company_policy", "allowed_authority_roles", optional=True, default="")
            if not author or role not in [r.strip() for r in roles.split(",")]:
                self.flags.append("unauthorized_amendment")
                continue
            target = self.pick(rows, "amends")
            if target != self.pick(base, "contract_id"):
                continue
            effective = self.pick(rows, "effective_date")
            if effective <= self.get("invoice", "invoice_date"):
                amendments.append((effective, rows))
        dates = sorted({d for d, _ in amendments})
        for day in dates:
            rows = [f for d, group in amendments if d == day for f in group]
            keys = {f.key for f in rows} - {
                "amends",
                "authorized_by",
                "authority_role",
                "effective_date",
            }
            for key in keys:
                self.pick(rows, key)
                base = [f for f in base if f.key != key] + [f for f in rows if f.key == key]
        return base

    def invoice_lines(self, sku):
        rows = [f for f in self.facts.facts if f.doc_kind == "invoice"]
        prefixes = sorted(
            {
                f.key.rsplit(".", 1)[0]
                for f in rows
                if f.key.startswith("line.") and f.key.endswith(".sku")
            }
        )
        result = []
        for prefix in prefixes:
            item_sku = self.pick(rows, prefix + ".sku")
            if sku is None or sku == item_sku:
                result.append(
                    (
                        item_sku,
                        self.pick(rows, prefix + ".qty"),
                        self.pick(rows, prefix + ".unit_price_cents"),
                    )
                )
        if not result:
            raise _Undecidable(Basis.missing_evidence, ["invoice line"])
        return result

    def delivered(self):
        pod = self.get("pod", "delivered_date", optional=True)
        tracking = self.get("tracking", "delivered_date", optional=True)
        if pod is not None and tracking is not None and pod != tracking:
            self.pick(
                [f for f in self.facts.facts if f.doc_kind in ("pod", "tracking")], "delivered_date"
            )
        value = pod if pod is not None else tracking
        if value is None:
            raise _Undecidable(Basis.missing_evidence, ["delivered_date"])
        return date.fromisoformat(value)

    def entitled(self, line):
        reason = line.reason
        if reason is None or reason == "unexplained_short_pay":
            raise _Undecidable(Basis.missing_evidence, ["reason"])
        if line.reason_trust in (FieldTrust.ocr, FieldTrust.vision):
            raise _Undecidable(Basis.untrusted_facts, ["reason"])
        if reason == "early_pay_discount":
            bp = self.term("early_pay_bp")
            days = self.term("early_pay_days")
            invoice = date.fromisoformat(self.get("invoice", "invoice_date"))
            paid = date.fromisoformat(self.get("payment", "paid_date"))
            total = self.get("invoice", "total_cents")
            return bp_of(total, bp) if paid <= invoice + timedelta(days=days) else 0
        if reason == "late_delivery":
            required = self.get("po", "required_delivery_date", optional=True)
            if required is None:
                required = self.term("required_delivery_date")
            delivered = self.delivered()
            bp, grace = self.term("late_penalty_bp"), self.term("late_grace_days")
            total = self.get("invoice", "total_cents")
            return (
                bp_of(total, bp)
                if delivered > date.fromisoformat(required) + timedelta(days=grace)
                else 0
            )
        if reason == "promo_rebate":
            if not line.buyer_ref:
                raise _Undecidable(Basis.missing_evidence, ["ref"])
            earned = self.term(f"promo.{line.buyer_ref}.earned")
            cap = self.term(f"promo.{line.buyer_ref}.cap_cents")
            return cap if earned else 0
        if reason == "nonpayment":
            if self.get("pod", "signed") is not True:
                raise _Undecidable(Basis.missing_evidence, ["signed POD"])
            if any(
                f.doc_kind == "email"
                and f.key.endswith(".reason")
                and _classified_email(
                    self.facts, f.evidence_id, f.key.rsplit(".", 1)[0], line.line_id
                )
                for f in self.facts.facts
            ):
                raise _Undecidable(Basis.missing_evidence, ["buyer dispute classification"])
            return 0
        if reason == "returns":
            required = self.term("returns_require_rma")
            docs = [d for d in self.facts.docs if d.kind == "return_auth"]
            if required and not docs:
                return 0
            if not docs or any(not d.readable for d in docs):
                raise _Undecidable(Basis.missing_evidence, ["return_auth"])
            qty = min(
                self.get("return_auth", "authorized_qty"), self.get("return_auth", "received_qty")
            )
            if line.qty is not None:
                qty = min(qty, line.qty)
            return qty * self.invoice_lines(line.sku)[0][2]
        items = self.invoice_lines(line.sku)
        if reason == "pricing":
            return sum(
                max(0, unit - self.term(f"price.{sku}_cents")) * qty for sku, qty, unit in items
            )
        if reason == "shortage":
            if self.get("pod", "signed") is not True:
                raise _Undecidable(Basis.missing_evidence, ["signed POD"])
            total = 0
            for sku, qty, unit in items:
                received = self.get("pod", f"received.{sku}")
                shipped = self.get("bol", f"shipped.{sku}", optional=True)
                if shipped is not None and shipped < qty:
                    self.flags.append("seller_short_shipped")
                total += (qty - received) * unit
            return total
        if reason == "damage":
            sku = line.sku or self.get("inspection", "sku")
            inspection_sku = self.get("inspection", "sku", optional=True)
            qty = (
                self.get("inspection", "damaged_qty", optional=True)
                if inspection_sku == sku
                else None
            )
            if qty is None:
                qty = self.get("pod", f"refused.{sku}")
                if not self.get("pod", "exception_note"):
                    raise _Undecidable(Basis.missing_evidence, ["exception_note"])
            reported = None
            for f in self.facts.facts:
                if f.key.endswith(".line_id") and f.value == line.line_id:
                    prefix = f.key.rsplit(".", 1)[0]
                    reported = self.pick(
                        [r for r in self.facts.facts if r.evidence_id == f.evidence_id],
                        prefix + ".reported_date",
                        optional=True,
                    )
                    if reported is not None:
                        break
            if reported is None:
                reported = self.get("inspection", "report_date")
            delivered, window = self.delivered(), self.term("damage_window_days")
            if date.fromisoformat(reported) > delivered + timedelta(days=window):
                if self.term("damage_late_waived", optional=True) is not True:
                    raise _Undecidable(Basis.unsupported_terms, ["damage_late_waived"])
                return 0
            return qty * self.invoice_lines(sku)[0][2]
        raise _Undecidable(Basis.unsupported_terms, ["reason"])


def _classified_email(facts, evidence_id, prefix, line_id):
    if not re.fullmatch(r"ded\.[1-9]\d*", prefix):
        return False
    rows = [f for f in facts.facts if f.evidence_id == evidence_id]
    senders = [f.value for f in rows if f.key == "from"]
    ids = [f.value for f in rows if f.key == prefix + ".line_id"]
    reasons = [f.value for f in rows if f.key == prefix + ".reason"]
    return (
        bool(senders)
        and all(v in facts.buyer_senders for v in senders)
        and bool(ids)
        and all(v == line_id for v in ids)
        and bool(reasons)
        and len(set(reasons)) == 1
        and reasons[0] in {r.value for r in DeductionReason if r != "nonpayment"}
        and all(
            f.trust not in {"ocr", "vision"}
            for f in rows
            if f.key in {"from", prefix + ".line_id", prefix + ".reason"}
        )
    )


def _legal_review(line, facts):
    signals = []
    for fact in facts.facts:
        if not re.fullmatch(r"ded\.[1-9]\d*\.requires_legal_review", fact.key):
            continue
        prefix = fact.key.rsplit(".", 1)[0]
        rows = [f for f in facts.facts if f.evidence_id == fact.evidence_id]
        if not any(f.key == prefix + ".line_id" and f.value == line.line_id for f in rows):
            continue
        if fact.doc_kind == "email" and not _classified_email(
            facts, fact.evidence_id, prefix, line.line_id
        ):
            continue
        if fact.doc_kind not in {"email", "remittance", "debit_memo"}:
            continue
        if type(fact.value) is not bool or fact.trust not in {"source", "human_confirmed"}:
            raise NeedsHumanError("legal review signal requires human confirmation")
        signals.append(fact.value)
    if len(set(signals)) > 1:
        raise NeedsHumanError("conflicting legal review signals")
    if any(signals):
        require_legal_authority(facts)


def run_rules(
    lines: list[DeductionLine], facts: FactSet, ledger: list[LedgerEntry]
) -> list[RuleFinding]:
    for line in lines:
        _legal_review(line, facts)
        if line.claimed.cents < 0:
            raise NeedsHumanError(f"negative deduction: {line.line_id}")
    findings = []
    for line in lines:
        flags = []
        ctx = None
        if line.claimed.cents == 0:
            findings.append(
                RuleFinding(
                    line_id=line.line_id,
                    rule_id=line.reason or "unclassified",
                    verdict=Verdict.valid,
                    basis=Basis.proven,
                    valid=Money(cents=0),
                    disputed=Money(cents=0),
                    citations=[],
                    note="SYNTHETIC rule result; design/02 §5.3",
                )
            )
            continue
        try:
            ctx = _Inputs(facts)
            flags = ctx.flags
            if line.reason is None or line.reason == "unexplained_short_pay":
                raise _Undecidable(Basis.missing_evidence, ["reason"])
            ctx.terms = ctx._contract()
            if any(e.kind == "credit_posted" and e.line_id == line.line_id for e in ledger):
                flags.append("already_credited")
            if line.buyer_ref and sum(x.buyer_ref == line.buyer_ref for x in lines) > 1:
                flags.append("duplicate_deduction_ref")
            if line.sku:
                try:
                    total = sum(q * u for _, q, u in ctx.invoice_lines(line.sku))
                except _Undecidable:
                    pass
                else:
                    if line.claimed.cents > total:
                        flags.append("claimed_exceeds_line_total")
            invoice = sum(e.amount.cents for e in ledger if e.kind == "invoice")
            paid = sum(e.amount.cents for e in ledger if e.kind == "payment")
            credit = sum(e.amount.cents for e in ledger if e.kind == "credit_posted")
            tolerance = ctx.get("company_policy", "tolerance_cents", optional=True, default=0)
            if (
                any(e.kind == "invoice" for e in ledger)
                and abs(invoice - paid - credit - sum(x.claimed.cents for x in lines)) > tolerance
            ):
                flags.append("remittance_math_mismatch")
            entitled = ctx.entitled(line) if line.claimed.cents else 0
            valid = clamp(entitled, 0, line.claimed.cents)
            if line.claimed.cents - valid <= tolerance:
                valid = line.claimed.cents
            disputed = line.claimed.cents - valid
            verdict = (
                Verdict.valid
                if valid == line.claimed.cents
                else (Verdict.invalid if valid == 0 else Verdict.partial)
            )
            finding = RuleFinding(
                line_id=line.line_id,
                rule_id=line.reason or "unclassified",
                verdict=verdict,
                basis=Basis.proven,
                valid=Money(cents=valid),
                disputed=Money(cents=disputed),
                citations=ctx.used,
                note="SYNTHETIC rule result; design/02 §5.3",
                flags=sorted(set(flags)),
            )
        except _Undecidable as exc:
            citations = ctx.used if ctx else []
            for pair in exc.contradictions:
                citations.extend(c for c in pair if c not in citations)
            finding = RuleFinding(
                line_id=line.line_id,
                rule_id=line.reason or "unclassified",
                verdict=Verdict.needs_info,
                basis=exc.basis,
                valid=None,
                disputed=None,
                missing=exc.missing,
                contradictions=exc.contradictions,
                citations=citations,
                note="SYNTHETIC unresolved rule; design/02 §5.3",
                flags=sorted(set(flags)),
            )
        findings.append(finding)
    return findings
