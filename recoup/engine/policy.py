"""Pure policy answers from design/02 §3.7 and §5.6."""

from datetime import date, timedelta

from recoup.contracts.models import Basis, FactSet, FieldTrust, Receipt
from recoup.contracts.tools import PolicyAnswer, PolicyQuestion


class _Unavailable(ValueError):
    def __init__(self, basis, note):
        self.basis, self.note = basis, note


def _rows(facts, kind, prefix):
    return sorted(
        [f for f in facts.facts if f.doc_kind == kind and f.key.startswith(prefix)],
        key=lambda f: (f.key, f.evidence_id),
    )


def _pick(facts, kind, key, expected=str):
    rows = [f for f in _rows(facts, kind, key) if f.key == key]
    if not rows:
        raise _Unavailable(Basis.missing_evidence, f"missing {key}")
    if any(f.trust in (FieldTrust.ocr, FieldTrust.vision) for f in rows):
        raise _Unavailable(Basis.untrusted_facts, f"unconfirmed {key}")
    if any(f.value != rows[0].value for f in rows[1:]):
        raise _Unavailable(Basis.contradiction, f"conflicting {key}")
    if type(rows[0].value) is not expected:
        raise _Unavailable(Basis.unsupported_terms, f"invalid {key}")
    return rows[0]


def _policy(facts, key, expected=str):
    return _pick(facts, "insurance_policy", key, expected)


def _date(fact):
    try:
        return date.fromisoformat(fact.value)
    except (TypeError, ValueError) as exc:
        raise _Unavailable(Basis.unsupported_terms, f"invalid {fact.key}") from exc


def _days(facts, key):
    fact = _policy(facts, key, int)
    if fact.value < 0:
        raise _Unavailable(Basis.unsupported_terms, f"negative {key}")
    return fact


def _keys(facts, prefix):
    return sorted({f.key for f in _rows(facts, "insurance_policy", prefix)})


def _receipt(receipts, facts, kind):
    return max(
        [r for r in receipts if r.business_key.startswith(f"{facts.case_id}:{kind}:")],
        key=lambda r: (r.at, r.receipt_id),
        default=None,
    )


def answer(facts: FactSet, q: PolicyQuestion, notice_receipt: Receipt | None) -> list[PolicyAnswer]:
    """Answer using only the supplied current facts and notice receipt (§5.6)."""

    def result(**kwargs):
        return PolicyAnswer(
            question=q,
            **{
                "applies": None,
                "value": None,
                "computed_date": None,
                "clause_citation": None,
                "basis": Basis.proven,
                "note": "",
                **kwargs,
            },
        )

    def textual(key, citation=None):
        clause = _policy(facts, f"clause.{key}")
        return result(
            clause_key=key, value=clause.value, clause_citation=citation or clause.citation
        )

    try:
        if q == "exclusions":
            keys = _keys(facts, "exclusion.")
            if not keys:
                raise _Unavailable(Basis.missing_evidence, "clause not established")
            answers = []
            for key in keys:
                try:
                    exclusion = _policy(facts, key)
                    answers.append(textual(exclusion.value, exclusion.citation))
                except _Unavailable as exc:
                    answers.append(result(basis=exc.basis, note=exc.note))
            return answers
        if q == "disputed_debt":
            key = _policy(facts, "disputed_debt_clause")
            return [textual(key.value)]
        if q == "applicability":
            buyer = _pick(facts, "invoice", "buyer_id")
            invoice_date = _date(_pick(facts, "invoice", "invoice_date"))
            keys = _keys(facts, "covered_buyer.")
            if not keys:
                raise _Unavailable(Basis.missing_evidence, "missing covered_buyer")
            buyers = [_policy(facts, key).value for key in keys]
            start = _date(_policy(facts, "period_start"))
            end = _date(_policy(facts, "period_end"))
            if start > end:
                raise _Unavailable(Basis.unsupported_terms, "invalid policy period")
            return [
                result(
                    applies=buyer.value in buyers and start <= invoice_date <= end,
                    clause_citation=_policy(facts, keys[0]).citation,
                )
            ]
        if q == "notice_deadline":
            due = _date(_pick(facts, "invoice", "due_date"))
            mep = _days(facts, "mep_days_after_due")
            notice = _days(facts, "notice_days_after_mep")
            return [
                result(
                    computed_date=due + timedelta(days=mep.value + notice.value),
                    clause_citation=notice.citation,
                )
            ]
        if q == "claim_window":
            if notice_receipt is None:
                raise _Unavailable(Basis.missing_evidence, "no notice receipt")
            if not notice_receipt.business_key.startswith(f"{facts.case_id}:insurer_notice:"):
                raise _Unavailable(Basis.missing_evidence, "no notice receipt")
            waiting = _days(facts, "waiting_days_after_notice")
            return [
                result(
                    computed_date=notice_receipt.at.date() + timedelta(days=waiting.value),
                    clause_citation=waiting.citation,
                )
            ]
        if q == "claim_documents":
            keys = _keys(facts, "claim_doc.")
            if not keys:
                raise _Unavailable(Basis.missing_evidence, "missing claim_doc")
            return [
                result(
                    value=_policy(facts, key).value, clause_citation=_policy(facts, key).citation
                )
                for key in keys
            ]
        if q == "credit_limit":
            limit = _policy(facts, "credit_limit_cents", int)
            if limit.value < 0:
                raise _Unavailable(Basis.unsupported_terms, "negative credit_limit_cents")
            return [result(value=str(limit.value), clause_citation=limit.citation)]
        raise ValueError(f"unknown policy question: {q}")
    except _Unavailable as exc:
        note = "clause not established" if q == "disputed_debt" else exc.note
        return [result(basis=exc.basis, note=note)]
    except (OverflowError, ValueError) as exc:
        if q not in ("notice_deadline", "claim_window"):
            raise
        return [result(basis=Basis.unsupported_terms, note=str(exc))]
