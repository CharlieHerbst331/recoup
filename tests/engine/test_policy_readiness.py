"""SYNTHETIC independent unit acceptance for 007-2; design/02 §3.7, §5.6."""

from datetime import date, timedelta

import pytest

from recoup.contracts.models import (
    Basis,
    Citation,
    DeductionLine,
    LineAmount,
    Receipt,
    RuleFinding,
)
from recoup.contracts.money import Money
from recoup.contracts.resolve import resolve_citation
from recoup.contracts.tools import CheckPolicyResult
from recoup.engine import policy, readiness

from .fixtures import NOW, fact_inputs

CASE = "synthetic-policy"


def inputs(
    *, changes=None, remove=(), pod="signed", confirmed=False, trust="source", collection=True
):
    terms = {
        "covered_buyer.1": "BUYER",
        "period_start": "2026-01-01",
        "period_end": "2026-12-31",
        "mep_days_after_due": 60,
        "notice_days_after_mep": 30,
        "waiting_days_after_notice": 60,
        "credit_limit_cents": 500000,
        "disputed_debt_clause": "excluded_until_resolved",
        "claim_doc.1": "invoice",
        "claim_doc.2": "pod",
        "claim_doc.3": "statement",
        "clause.excluded_until_resolved": "SYNTHETIC disputed amounts restricted until resolved.",
        "clause.notice_still_required": "SYNTHETIC notice still required for disputed debt.",
        "clause.exclusion_a": "SYNTHETIC exclusion A.",
        "clause.exclusion_b": "SYNTHETIC exclusion B.",
    }
    terms.update(changes or {})
    for key in remove:
        terms.pop(key, None)
    docs = [
        {"id": "policy", "kind": "insurance_policy", "fields": terms},
        {
            "id": "invoice",
            "kind": "invoice",
            "fields": {
                "buyer_id": "BUYER",
                "invoice_date": "2026-08-03",
                "due_date": "2026-09-02",
                "total_cents": 100000,
            },
        },
        {"id": "statement", "kind": "statement", "fields": {}},
    ]
    if pod != "absent":
        docs.append(
            {
                "id": "pod",
                "kind": "pod",
                "readable": pod != "unreadable",
                "fields": {"signed": pod == "signed"},
                "confirmed": confirmed,
                "trust": trust,
            }
        )
    if collection:
        docs.append({"id": "collection", "kind": "collection_note", "fields": {}})
    return fact_inputs(docs, CASE)


def ledger():
    from recoup.contracts.models import LedgerEntry

    return [
        LedgerEntry(
            entry_id="L",
            case_id=CASE,
            kind="invoice",
            amount=Money(cents=100000),
            line_id=None,
            source="SYNTHETIC",
            at=NOW,
        )
    ]


def receipt(kind="insurer_notice", days=0, line="A"):
    return Receipt(
        receipt_id=f"MOCK-{kind}-{days}",
        proposal_id="P",
        proposal_version=1,
        business_key=f"{CASE}:{kind}:{line}",
        idempotency_key=f"I-{kind}-{days}",
        target=(
            "mock_insurer"
            if kind == "insurer_notice"
            else "mock_email"
            if kind == "follow_up"
            else "mock_buyer_portal"
        ),
        amount=Money(cents=100),
        at=NOW + timedelta(days=days),
        allocations=[LineAmount(line_id=line, amount=Money(cents=100))],
    )


def finding(line="A", **changes):
    return RuleFinding(
        **{
            "line_id": line,
            "rule_id": "shortage",
            "verdict": "invalid",
            "basis": "proven",
            "valid": Money(cents=0),
            "disputed": Money(cents=100),
            "citations": [],
            "note": "",
            **changes,
        }
    )


def items(result):
    return {item.item_id: item for item in result.items}


def test_two_lines_isolated_confirmed_and_unconfirmed():
    facts, _, _ = inputs(confirmed=True)
    confirmed = next(f.citation for f in facts.facts if f.key == "signed")
    line_a = DeductionLine(line_id="A", reason="shortage", claimed=Money(cents=100))
    line_b = line_a.model_copy(update={"line_id": "B"})
    # Both lines use the exact same FactSet, including a separate unconfirmed OCR fact.
    ocr, _, _ = fact_inputs(
        [{"id": "ocr", "kind": "pod", "trust": "ocr", "fields": {"signed": True}}], CASE
    )
    facts.facts.extend(ocr.facts)
    facts.docs.extend(ocr.docs)
    assert readiness.dispute(line_a, finding(citations=[confirmed]), facts).status == "ready"
    blocked = readiness.dispute(line_b, finding("B", citations=[ocr.facts[0].citation]), facts)
    assert blocked.status == "not_ready" and blocked.line_id == "B"
    conflict = finding(
        "B", citations=[confirmed], contradictions=[(confirmed, ocr.facts[0].citation)]
    )
    assert readiness.dispute(line_b, conflict, facts).status == "not_ready"
    assert readiness.dispute(line_a, finding(citations=[confirmed]), facts).line_id == "A"
    with pytest.raises(ValueError, match="mismatch"):
        readiness.dispute(line_a, finding("B"), facts)


def test_dispute_citations_current_membership_and_resolver():
    facts, evidence, revisions = inputs(confirmed=True)
    citation = next(f.citation for f in facts.facts if f.key == "signed")
    assert resolve_citation(citation, facts, evidence, revisions) is True
    line = DeductionLine(line_id="A", reason="shortage", claimed=Money(cents=100))
    for bad in [
        citation.model_copy(update={"quote": "false"}),
        citation.model_copy(update={"locator": "fact:old"}),
        Citation(evidence_id="missing", locator="text", quote="invented"),
    ]:
        result = readiness.dispute(line, finding(citations=[bad]), facts)
        assert result.status == "not_ready"
        assert items(result)["dispute.A.citations"].status == "unknown"


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({}, date(2026, 12, 1)),
        (
            {
                "mep_days_after_due": 30,
                "notice_days_after_mep": 10,
                "disputed_debt_clause": "notice_still_required",
            },
            date(2026, 10, 12),
        ),
    ],
)
def test_contrasting_policies(changes, expected):
    facts, _, _ = inputs(changes=changes)
    assert policy.answer(facts, "notice_deadline", None)[0].computed_date == expected
    result = readiness.notice(facts, ledger(), [], NOW.date(), [finding()])
    assert result.deadline == expected and result.status == "ready"
    assert items(result)["notice.dispute_status"].status == ("present" if changes else "restricted")
    claim = readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1))
    assert items(claim)["claim.disputed_portion"].status == ("present" if changes else "restricted")


def test_claim_window_uses_receipt_date_and_latest_receipt():
    facts, _, _ = inputs(changes={"disputed_debt_clause": "notice_still_required"})
    for day in (0, 4):
        result = policy.answer(facts, "claim_window", receipt(days=day))[0]
        assert result.computed_date == NOW.date() + timedelta(days=60 + day)
    missing = policy.answer(facts, "claim_window", None)[0]
    assert missing.basis == Basis.missing_evidence
    assert missing.computed_date is None and missing.note == "no notice receipt"
    assert policy.answer(facts, "claim_window", receipt("dispute"))[0].computed_date is None
    result = readiness.claim(
        facts, ledger(), [receipt(), receipt(days=4)], NOW.date() + timedelta(days=60)
    )
    assert items(result)["claim.waiting_period"].status == "missing"
    result = readiness.claim(
        facts, ledger(), [receipt(), receipt(days=4)], NOW.date() + timedelta(days=64)
    )
    assert result.status == "ready"


def test_exclusions_extracted_fact_citations_survive_json():
    facts, evidence, revisions = inputs()
    evidence[0].text = "SYNTHETIC exclusion A exists only in this text."
    assert policy.answer(facts, "exclusions", None)[0].basis == Basis.missing_evidence
    source, _, _ = fact_inputs(
        [
            {
                "id": "source-exclusion",
                "kind": "insurance_policy",
                "fields": {"exclusion.1": "exclusion_a"},
            }
        ],
        CASE,
    )
    extracted, ev, rev = fact_inputs(
        [
            {
                "id": "extracted-exclusion",
                "kind": "insurance_policy",
                "confirmed": True,
                "fields": {"exclusion.2": "exclusion_b"},
            }
        ],
        CASE,
    )
    # Model-extracted revision cites text; no source field is fabricated for it.
    ev[0].text = "SYNTHETIC clause key exclusion_b."
    ev[0].fields = {}
    rev[0] = rev[0].model_copy(
        update={
            "trust": "model_extracted",
            "citation": Citation(
                evidence_id=ev[0].evidence_id, locator="text", quote="exclusion_b"
            ),
        }
    )
    extracted.facts[0] = extracted.facts[0].model_copy(update={"trust": "model_extracted"})
    facts.facts.extend(extracted.facts)
    facts.docs.extend(extracted.docs)
    one = policy.answer(facts, "exclusions", None)
    assert len(one) == 1 and one[0].clause_citation == extracted.facts[0].citation
    facts.facts.extend(source.facts)
    facts.docs.extend(source.docs)
    answers = policy.answer(facts, "exclusions", None)
    restored = CheckPolicyResult.model_validate_json(
        CheckPolicyResult(answers=answers).model_dump_json()
    )
    assert restored.answers == answers and len(answers) == 2
    assert {a.clause_key for a in answers} == {"exclusion_a", "exclusion_b"}
    assert {a.clause_citation.locator for a in answers} == {
        "fields.exclusion.1",
        extracted.facts[0].citation.locator,
    }
    assert resolve_citation(one[0].clause_citation, facts, ev, rev) == "exclusion_b"


@pytest.mark.parametrize(
    "findings,status,note",
    [
        (None, "unknown", "not computed"),
        (
            [finding("B", verdict="needs_info", basis="missing_evidence", missing=["pod"])],
            "unknown",
            "B: pod",
        ),
        ([finding(rule_id="nonpayment")], "present", "no buyer dispute"),
        ([finding()], "restricted", "established, not submitted"),
        ([finding(verdict="valid")], "present", "no buyer dispute"),
    ],
)
def test_notice_independence(findings, status, note):
    facts, _, _ = inputs(pod="absent")
    result = readiness.notice(facts, ledger(), [], NOW.date(), findings)
    annotation = items(result)["notice.dispute_status"]
    assert result.status == "ready"
    assert annotation.status == status and note in annotation.note
    assert result.balance_basis == Money(cents=100000)
    assert result.evidence_set_hash == facts.basis_hash


def test_notice_submitted_unknown_clause_and_applicability():
    facts, _, _ = inputs()
    result = readiness.notice(facts, ledger(), [receipt("dispute")], NOW.date(), [finding()])
    assert items(result)["notice.dispute_status"].note == "A: submitted"
    facts, _, _ = inputs(remove=["disputed_debt_clause"])
    result = readiness.notice(facts, ledger(), [], NOW.date(), [finding()])
    assert result.status == "ready"
    assert items(result)["notice.dispute_status"].status == "unknown"
    facts, _, _ = inputs(remove=["covered_buyer.1"])
    assert readiness.notice(facts, ledger(), [], NOW.date(), []).status == "not_ready"
    facts, _, _ = inputs(remove=["notice_days_after_mep"])
    assert readiness.notice(facts, ledger(), [], NOW.date(), []).status == "not_ready"


@pytest.mark.parametrize(
    "pod,status",
    [
        ("absent", "missing"),
        ("unreadable", "defective"),
        ("unsigned", "defective"),
        ("signed", "present"),
    ],
)
def test_claim_pod_inventory(pod, status):
    facts, _, _ = inputs(pod=pod)
    result = readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1))
    checklist = items(result)
    assert checklist["claim.doc.pod"].status == status
    assert set(checklist) == {
        "claim.notice_receipt",
        "claim.waiting_period",
        "claim.doc.invoice",
        "claim.doc.pod",
        "claim.doc.statement",
        "claim.collection_history",
        "claim.disputed_portion",
        "claim.credit_limit",
    }
    if pod == "unreadable":
        assert checklist["claim.doc.pod"].note == "empty_text"
    assert "eligibility" not in result.model_dump_json()


def test_claim_checklist_restrictions_missing_and_history():
    facts, _, _ = inputs(changes={"credit_limit_cents": 99999}, collection=False)
    result = readiness.claim(facts, ledger(), [], NOW.date())
    checklist = items(result)
    assert result.status == "not_ready"
    assert checklist["claim.notice_receipt"].status == "missing"
    assert checklist["claim.waiting_period"].status == "unknown"
    assert checklist["claim.collection_history"].status == "missing"
    assert checklist["claim.disputed_portion"].status == "restricted"
    assert checklist["claim.credit_limit"].status == "restricted"
    result = readiness.claim(facts, ledger(), [receipt(), receipt("follow_up")], date(2027, 1, 1))
    assert items(result)["claim.collection_history"].status == "present"
    assert result.balance_basis == Money(cents=100000)


@pytest.mark.parametrize(
    "changes,applies",
    [
        ({}, True),
        ({"covered_buyer.1": "OTHER"}, False),
        ({"period_start": "2026-08-03", "period_end": "2026-08-03"}, True),
        ({"period_start": "2026-08-04"}, False),
    ],
)
def test_applicability(changes, applies):
    facts, _, _ = inputs(changes=changes)
    result = policy.answer(facts, "applicability", None)[0]
    assert result.applies is applies and result.basis == Basis.proven


def test_textual_answers_require_effective_clause_facts():
    facts, _, _ = inputs()
    result = policy.answer(facts, "disputed_debt", None)[0]
    assert result.value == "SYNTHETIC disputed amounts restricted until resolved."
    assert result.clause_citation == next(
        f.citation for f in facts.facts if f.key == "clause.excluded_until_resolved"
    )
    facts, _, _ = inputs(remove=["clause.excluded_until_resolved"])
    result = policy.answer(facts, "disputed_debt", None)[0]
    assert result.value is None and result.applies is None
    assert result.basis == Basis.missing_evidence and result.note == "clause not established"


@pytest.mark.parametrize(
    "changes,basis",
    [
        ({"notice_days_after_mep": -1}, "unsupported_terms"),
        ({"mep_days_after_due": "60"}, "unsupported_terms"),
        ({"waiting_days_after_notice": True}, "unsupported_terms"),
    ],
)
def test_invalid_policy_terms(changes, basis):
    facts, _, _ = inputs(changes=changes)
    question = "claim_window" if "waiting_days_after_notice" in changes else "notice_deadline"
    assert policy.answer(facts, question, receipt())[0].basis == basis


def test_policy_untrusted_conflict_and_purity():
    facts, _, _ = inputs()
    before = facts.model_dump_json()
    for question in (
        "applicability",
        "notice_deadline",
        "claim_window",
        "claim_documents",
        "disputed_debt",
        "credit_limit",
        "exclusions",
    ):
        policy.answer(facts, question, receipt())
    readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1))
    readiness.notice(facts, ledger(), [], NOW.date(), [])
    assert facts.model_dump_json() == before
    duplicate = next(f for f in facts.facts if f.key == "notice_days_after_mep")
    facts.facts.append(duplicate.model_copy(update={"value": 31, "evidence_id": "other"}))
    assert policy.answer(facts, "notice_deadline", None)[0].basis == Basis.contradiction
    facts.facts.pop()
    facts.facts = [
        f.model_copy(update={"trust": "ocr"}) if f == duplicate else f for f in facts.facts
    ]
    assert policy.answer(facts, "notice_deadline", None)[0].basis == Basis.untrusted_facts


def test_exclusion_failure_does_not_hide_other_exclusions():
    facts, _, _ = inputs(changes={"exclusion.1": "exclusion_a", "exclusion.2": "unknown_clause"})
    answers = policy.answer(facts, "exclusions", None)
    assert len(answers) == 2
    assert answers[0].basis == Basis.proven
    assert answers[1].basis == Basis.missing_evidence


def test_claim_documents_multiple_candidates_and_same_evidence_signature():
    facts, _, _ = inputs(pod="unsigned", changes={"disputed_debt_clause": "notice_still_required"})
    extra, _, _ = fact_inputs(
        [{"id": "other-pod", "kind": "pod", "fields": {"signed": True}}], CASE
    )
    facts.facts.extend(extra.facts)
    # A signature not belonging to an inventoried POD cannot complete it.
    assert (
        items(readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1)))[
            "claim.doc.pod"
        ].status
        == "defective"
    )
    facts.docs.extend(extra.docs)
    result = readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1))
    assert result.status == "ready"
    assert items(result)["claim.doc.pod"].satisfied_by == ["other-pod"]


def test_claim_unconfirmed_pod_and_missing_policy_terms():
    facts, _, _ = inputs(trust="vision")
    assert (
        items(readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1)))[
            "claim.doc.pod"
        ].status
        == "defective"
    )
    facts, _, _ = inputs(
        remove=[
            "claim_doc.1",
            "claim_doc.2",
            "claim_doc.3",
            "credit_limit_cents",
            "disputed_debt_clause",
        ]
    )
    result = readiness.claim(facts, ledger(), [receipt()], date(2027, 1, 1))
    assert result.status == "not_ready"
    assert items(result)["claim.credit_limit"].status == "unknown"
    assert items(result)["claim.disputed_portion"].status == "unknown"
    assert items(result)["claim.documents"].status == "unknown"


def test_notice_due_boundary_and_net_ledger_balance():
    facts, _, _ = inputs()
    entries = ledger()
    entries.append(entries[0].model_copy(update={"kind": "payment", "amount": Money(cents=40000)}))
    entries.append(
        entries[0].model_copy(update={"kind": "credit_posted", "amount": Money(cents=10000)})
    )
    result = readiness.notice(facts, entries, [], date(2026, 9, 2), [])
    assert result.balance_basis == Money(cents=50000)
    assert items(result)["notice.trigger"].status == "missing"
    assert readiness.notice(facts, entries, [], date(2026, 9, 3), []).status == "ready"
    entries.append(entries[0].model_copy(update={"kind": "payment", "amount": Money(cents=50000)}))
    assert readiness.notice(facts, entries, [], NOW.date(), []).status == "not_ready"


def test_case_identity_does_not_select_policy_behavior():
    facts, _, _ = inputs()
    changed = facts.model_copy(update={"case_id": "another-synthetic-case"})
    for q in (
        "applicability",
        "notice_deadline",
        "claim_documents",
        "disputed_debt",
        "credit_limit",
        "exclusions",
    ):
        assert policy.answer(facts, q, None) == policy.answer(changed, q, None)
