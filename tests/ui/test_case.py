"""Case tables and history presentation through app-built fixtures (design/02 §6)."""

from datetime import timedelta, timezone

import pytest

from recoup.contracts.models import (
    Approval,
    Citation,
    Decision,
    DomainEvent,
    LineDecision,
    Readiness,
    ReadinessItem,
    Receipt,
)
from recoup.contracts.money import Money
from recoup.ui.case import group_readiness, money_table, timeline_rows


def decision(case, lines):
    return Decision(
        decision_id="decision-1",
        case_id=case.case_id,
        version=1,
        evidence_set_hash="SYNTHETIC-basis",
        lines=lines,
        current=True,
        model_id="offline-fakellm",
        llm_mode="fake",
        prompt_version="v1",
        created_at=case.sim_now,
    )


def test_money_table_matches_lines_by_id_without_summing_tracks(service):
    case = service.world.view("H")
    amounts = [
        ("valid", 101, 101, 0),
        ("invalid", 203, 0, 203),
        ("partial", 305, 100, 205),
        ("needs_info", 407, None, None),
    ]
    lines = [
        case.lines[0].model_copy(update={"line_id": verdict, "claimed": Money(cents=claimed)})
        for verdict, claimed, _, _ in amounts
    ]
    decisions = [
        LineDecision(
            line_id=verdict,
            verdict=verdict,
            basis="missing_evidence" if valid is None else "proven",
            valid=Money(cents=valid) if valid is not None else None,
            disputed=Money(cents=disputed) if disputed is not None else None,
            citations=[],
            rationale="SYNTHETIC test",
        )
        for verdict, _, valid, disputed in reversed(amounts)
    ]
    case = case.model_copy(update={"lines": lines, "decision": decision(case, decisions)})
    rows = money_table(case)
    assert [row["Item"] for row in rows] == [
        "Invoice total",
        "Open balance",
        "valid",
        "invalid",
        "partial",
        "needs_info",
    ]
    assert [
        (row["Claimed (USD)"], row["Verdict"], row["Valid (USD)"], row["Disputed (USD)"])
        for row in rows[2:]
    ] == [
        ("$1.01", "valid", "$1.01", "$0.00"),
        ("$2.03", "invalid", "$0.00", "$2.03"),
        ("$3.05", "partial", "$1.00", "$2.05"),
        ("$4.07", "needs_info", "Unknown", "Unknown"),
    ]
    assert all(row["Amount (USD)"] == "" for row in rows[2:])
    assert all(row["Claimed (USD)"] == "" for row in rows[:2])


@pytest.mark.parametrize(
    ("cents", "expected"),
    [(0, "$0.00"), (-101, "-$1.01"), (100000000000000001, "$1,000,000,000,000,000.01")],
)
def test_table_formats_money_exactly_and_leaves_undecided_amounts_unknown(service, cents, expected):
    case = service.world.view("H")
    line = case.lines[0].model_copy(update={"claimed": Money(cents=cents)})
    case = case.model_copy(
        update={
            "invoice_total": Money(cents=cents),
            "open_balance": Money(cents=cents),
            "lines": [line],
            "decision": None,
        }
    )
    rows = money_table(case)
    assert len(rows) == 3
    assert rows[0]["Amount (USD)"] == rows[1]["Amount (USD)"] == expected
    assert rows[2]["Claimed (USD)"] == expected
    assert rows[2]["Verdict"] == "Pending decision"
    assert rows[2]["Valid (USD)"] == rows[2]["Disputed (USD)"] == "Unknown"
    partial = case.model_copy(update={"decision": decision(case, [])})
    assert money_table(partial) == rows
    assert len(money_table(case.model_copy(update={"lines": []}))) == 2


def test_readiness_groups_preserve_line_assessments_and_policy_citations(service):
    case = service.world.view("H")
    citation = Citation(evidence_id="policy-1", locator="text:1", quote="SYNTHETIC policy")
    records = [
        Readiness(
            readiness_id=f"ready-{index}",
            case_id="H",
            kind=kind,
            line_id=f"line-{index}" if kind == "dispute" else None,
            status="not_ready",
            evidence_set_hash="SYNTHETIC-basis",
            items=[
                ReadinessItem(
                    item_id=f"item-{index}",
                    requirement="Document",
                    status="missing",
                    policy_citation=citation,
                )
            ],
        )
        for index, kind in enumerate(["claim", "dispute", "notice", "dispute"])
    ]
    grouped = group_readiness(case.model_copy(update={"readiness": records}))
    assert list(grouped) == ["dispute", "notice", "claim"]
    assert grouped == {
        "dispute": [records[1], records[3]],
        "notice": [records[2]],
        "claim": [records[0]],
    }
    assert group_readiness(case.model_copy(update={"readiness": []})) == {
        "dispute": [],
        "notice": [],
        "claim": [],
    }


def test_timeline_merges_all_history_categories_and_preserves_versions(service):
    case = service.world.view("H")
    history = service.history("H")
    now = case.sim_now
    evidence = history.evidence_all[0].model_copy(
        update={
            "available_from": (now + timedelta(hours=1)).replace(tzinfo=None),
            "active": False,
            "superseded_by": "evidence-v2",
        }
    )
    newer_evidence = evidence.model_copy(
        update={
            "evidence_id": "evidence-v2",
            "version": 2,
            "active": True,
            "superseded_by": None,
            "available_from": now + timedelta(hours=2),
        }
    )
    old_decision = decision(case, []).model_copy(update={"current": False})
    new_decision = old_decision.model_copy(
        update={
            "decision_id": "decision-2",
            "version": 2,
            "current": True,
            "created_at": (now + timedelta(hours=3)).astimezone(timezone(timedelta(hours=-7))),
        }
    )
    approval = Approval(
        approval_id="approval-1",
        proposal_id="proposal-1",
        proposal_version=2,
        recipient="mock-recipient",
        amount=Money(cents=100000000000000001),
        draft_sha256="draft",
        evidence_set_hash="basis",
        decision_version=2,
        approver="SYNTHETIC approver",
        approved=False,
        reason="Missing evidence",
        void=True,
        void_reason="Stale basis",
        at=now + timedelta(hours=4),
    )
    receipt = Receipt(
        receipt_id="MOCK-1",
        proposal_id="proposal-1",
        proposal_version=1,
        business_key="H:dispute:line",
        idempotency_key="key",
        target="mock_buyer_portal",
        amount=Money(cents=101),
        at=now + timedelta(hours=5),
    )
    events = [
        DomainEvent(
            event_id=f"event-{seq}",
            case_id="H",
            seq=seq,
            at=now + timedelta(hours=6),
            type="evidence_added",
            ref="evidence-v2",
        )
        for seq in (2, 1)
    ]
    history = history.model_copy(
        update={
            "evidence_all": [newer_evidence, evidence],
            "decisions": [new_decision, old_decision],
            "approvals": [approval],
            "receipts": [receipt],
            "events": events,
        }
    )
    before = history.model_dump_json()
    rows = timeline_rows(history)
    assert [(row["Type"], row["Reference"]) for row in rows] == [
        ("Decision", "decision-1"),
        ("Evidence", evidence.evidence_id),
        ("Evidence", "evidence-v2"),
        ("Decision", "decision-2"),
        ("Approval", "approval-1"),
        ("MOCK receipt", "MOCK-1"),
        ("Event", "event-1"),
        ("Event", "event-2"),
    ]
    assert "v1; current=False; LLM: fake (offline-fakellm)" in rows[0]["Detail"]
    assert "superseded by evidence-v2" in rows[1]["Detail"]
    assert rows[1]["At (UTC)"] == (now + timedelta(hours=1)).isoformat()
    assert rows[3]["At (UTC)"] == (now + timedelta(hours=3)).isoformat()
    assert "rejected by SYNTHETIC approver" in rows[4]["Detail"]
    assert "$1,000,000,000,000,000.01" in rows[4]["Detail"]
    assert "reason=Missing evidence; void=True; void reason=Stale basis" in rows[4]["Detail"]
    assert receipt.label in rows[5]["Detail"]
    assert "$1.01" in rows[5]["Detail"]
    assert history.model_dump_json() == before
    assert (
        timeline_rows(
            history.model_copy(
                update={
                    "evidence_all": [],
                    "decisions": [],
                    "approvals": [],
                    "receipts": [],
                    "events": [],
                }
            )
        )
        == []
    )
