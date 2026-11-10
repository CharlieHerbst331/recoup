from datetime import timedelta

import pytest

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.interfaces import GateError
from recoup.contracts.models import (
    Citation,
    Decision,
    DueWork,
    FieldTrust,
    GateIssue,
    LineAmount,
    Money,
    Proposal,
)
from recoup.contracts.resolve import resolve_citation
from recoup.contracts.testing import stub_parts
from recoup.world import SqliteWorld


def proposal(world, **updates):
    p = Proposal(
        proposal_id="P",
        business_key="CASE:info_request:U1",
        version=1,
        case_id="CASE",
        kind="info_request",
        target="mock_email",
        recipient="buyer@example.test",
        allocations=[],
        amount=None,
        draft_text="Please explain the short payment.",
        draft_sha256="",
        citations=[],
        decision_id=None,
        decision_version=None,
        evidence_set_hash=world.evidence_set_hash("CASE"),
        status="proposed",
        created_at=world.clock.now(),
        created_by="agent",
    )
    return p.model_copy(update=updates)


def doc(world, ref="POD"):
    return next(e for e in world.active_evidence("CASE") if e.doc_ref == ref)


def test_quarantine_has_no_case_evidence_ledger_or_money(world, bundle):
    bundle.currency = "EUR"
    assert world.load_bundle(bundle).status == "quarantined"
    assert world.list_cases() == []
    assert world.db.execute("SELECT count(*) FROM ledger").fetchone()[0] == 0
    assert world.db.execute("SELECT count(*) FROM evidence").fetchone()[0] == 0
    assert '"currency":"EUR"' in world.list_quarantined()[0].raw_bundle_json
    with pytest.raises(GateError, match="unknown_case"):
        world.view("CASE")


def test_ledger_lines_and_allowed_recipients(world, bundle):
    world.load_bundle(bundle)
    assert world.ledger_balance("CASE").cents == 2000
    assert [e.kind for e in world.ledger("CASE")] == ["invoice", "payment"]
    assert world.deduction_lines("CASE")[0].reason == "unexplained_short_pay"
    assert world.deduction_lines("CASE")[0].claimed.cents == 2000
    recipients = world.allowed_recipients("CASE", proposal(world).target)
    recipients.clear()
    assert world.allowed_recipients("CASE", proposal(world).target) == ["buyer@example.test"]
    world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="CM",
            kind="credit_memo",
            title="Prior credit",
            fields={"amount_cents": 500, "line_id": "U1"},
        ),
    )
    assert world.ledger_balance("CASE").cents == 1500
    assert world.deduction_lines("CASE")[0].claimed.cents == 1500


def test_supersession_reverse_order_duplicate_and_conflict(world, bundle):
    world.load_bundle(bundle)
    old = doc(world)
    stored = world.db.execute(
        "SELECT data FROM evidence WHERE id=?", (old.evidence_id,)
    ).fetchone()[0]
    v3 = world.add_evidence(
        "CASE", BundleDoc(doc_ref="POD", version=3, kind="pod", title="POD", text="Third")
    )
    v2doc = BundleDoc(doc_ref="POD", version=2, kind="pod", title="POD", text="Second")
    v2 = world.add_evidence("CASE", v2doc)
    assert not v2.active and v2.superseded_by == v3.evidence_id
    assert world.evidence(old.evidence_id).superseded_by == v3.evidence_id
    assert (
        world.db.execute("SELECT data FROM evidence WHERE id=?", (old.evidence_id,)).fetchone()[0]
        == stored
    )
    hashed = world.evidence_set_hash("CASE")
    assert world.add_evidence("CASE", v2doc) is None
    assert world.evidence_set_hash("CASE") == hashed
    assert world.history("CASE").events[-1].type == "duplicate_ignored"
    assert world.add_evidence("CASE", v2doc.model_copy(update={"text": "conflict"})) is None
    assert world.view("CASE").status == "needs_human"
    assert world.evidence_set_hash("CASE") == hashed
    with pytest.raises(GateError, match="superseded_citation"):
        world.resolve_citation(
            Citation(evidence_id=old.evidence_id, locator="text", quote="80 cases")
        )


def test_fact_flow_immutable_rows_and_historical_basis(world, bundle):
    world.load_bundle(bundle)
    row = doc(world)
    raw = world.db.execute("SELECT data FROM evidence WHERE id=?", (row.evidence_id,)).fetchone()[0]
    source_basis = world.fact_set("CASE")
    assert not any(f.key == "received.SKU-1" for f in source_basis.facts)
    source = Citation(evidence_id=row.evidence_id, locator="text", quote="Received 80 cases.")
    first = world.add_fact(
        row.evidence_id, "received.SKU-1", 80, FieldTrust.model_extracted, source, "model"
    )
    extracted_basis = world.fact_set("CASE")
    assert first == world.add_fact(row.evidence_id, first.key, 80, first.trust, source, "model")
    assert world.fact_set("CASE") == extracted_basis
    confirmed = world.confirm_field(row.evidence_id, first.key, "Charles")
    old_basis = world.fact_set("CASE")
    old_citation = next(f.citation for f in old_basis.facts if f.key == first.key)
    assert confirmed.supersedes_fact_id == first.fact_id
    assert old_basis.basis_hash != extracted_basis.basis_hash
    assert next(f for f in old_basis.facts if f.key == first.key).trust == "human_confirmed"
    later = world.add_fact(
        row.evidence_id,
        first.key,
        90,
        FieldTrust.model_extracted,
        Citation(evidence_id=row.evidence_id, locator="text", quote="Received 90 cases."),
        "model",
    )
    assert later.supersedes_fact_id == confirmed.fact_id
    assert world.fact_set("CASE", old_basis.basis_hash) == old_basis
    assert world.resolve_citation(old_citation, old_basis.basis_hash) == 80
    assert (
        resolve_citation(
            old_citation, old_basis, world.history("CASE").evidence_all, world.history("CASE").facts
        )
        == 80
    )
    with pytest.raises(GateError, match="superseded_citation"):
        world.resolve_citation(old_citation)
    assert (
        world.db.execute("SELECT data FROM evidence WHERE id=?", (row.evidence_id,)).fetchone()[0]
        == raw
    )
    assert world.evidence(row.evidence_id).fields == {"signed": True}
    assert old_basis.docs[0].readable


def test_source_confirmation_bool_quote_and_fact_noop(world, bundle):
    world.load_bundle(bundle)
    row = doc(world)
    first = world.confirm_field(row.evidence_id, "signed", "Charles")
    assert first.citation.quote == "true"
    assert world.confirm_field(row.evidence_id, "signed", "Charles") == first
    assert (
        world.resolve_citation(
            next(f.citation for f in world.fact_set("CASE").facts if f.key == "signed")
        )
        is True
    )


def test_transaction_rolls_back_every_table_and_clock(world, bundle):
    tables = [
        r[0]
        for r in world.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    before = {t: world.db.execute(f"SELECT * FROM {t}").fetchall() for t in tables}
    with pytest.raises(RuntimeError, match="rollback"):
        with world.transaction():
            world.load_bundle(bundle)
            world.save_proposal(proposal(world))
            world.confirm_field(doc(world).evidence_id, "signed", "Charles")
            world.advance_to(4, release_events=False)
            world.schedule(
                DueWork(
                    due_id="DUE",
                    case_id="CASE",
                    kind="recheck",
                    due_at=world.clock.now(),
                    basis="P",
                    idempotency_key="due",
                )
            )
            raise RuntimeError("rollback")
    assert {t: world.db.execute(f"SELECT * FROM {t}").fetchall() for t in tables} == before
    assert world.clock.day() == 0


def test_nested_transaction_rollback_keeps_outer_work(world, bundle):
    with world.transaction():
        world.load_bundle(bundle)
        with pytest.raises(RuntimeError):
            with world.transaction():
                world.save_proposal(proposal(world))
                raise RuntimeError()
    assert world.list_cases()
    assert not world.history("CASE").proposals_all


def test_proposal_identity_versioning_edits_approval_and_reject(world, bundle):
    world.load_bundle(bundle)
    p1 = world.save_proposal(proposal(world))
    assert world.save_proposal(proposal(world, proposal_id="OTHER")) == p1
    assert len(world.history("CASE").proposals_all) == 1
    p2 = world.edit_proposal(
        p1.proposal_id, p1.version, draft_text="Please provide the remittance."
    )
    assert p2.version == 2 and p2.proposal_id == p1.proposal_id
    approval = world.approve(p2.proposal_id, 2, "Charles")
    assert approval.draft_sha256 == p2.draft_sha256
    with pytest.raises(GateError, match="immutable_proposal"):
        world.edit_proposal(p2.proposal_id, 2, draft_text="changed")
    p3 = world.save_proposal(proposal(world, draft_text="Revised request."))
    assert p3.version == 3
    assert world.history("CASE").approvals[0].void
    with pytest.raises(GateError, match="reason_required"):
        world.reject(p3.proposal_id, 3, "Charles", " ")
    assert not world.reject(p3.proposal_id, 3, "Charles", "Need another draft").approved
    assert world.view("CASE").proposals[0].status == "rejected"


def test_edit_recipient_and_allocation_limits(world, bundle):
    world.load_bundle(bundle)
    p = world.save_proposal(
        proposal(
            world,
            allocations=[LineAmount(line_id="U1", amount=Money(cents=2000))],
            amount=Money(cents=2000),
        )
    )
    with pytest.raises(GateError, match="recipient_not_allowed"):
        world.edit_proposal(p.proposal_id, 1, recipient="stranger@example.test")
    with pytest.raises(GateError, match="allocation_increase"):
        world.edit_proposal(
            p.proposal_id, 1, allocations=[LineAmount(line_id="U1", amount=Money(cents=2001))]
        )
    p2 = world.edit_proposal(
        p.proposal_id, 1, allocations=[LineAmount(line_id="U1", amount=Money(cents=1500))]
    )
    assert p2.amount.cents == 1500


def test_validator_is_called_at_save_and_approve_and_rolls_back(world, bundle):
    class Validator:
        def __init__(self):
            self.calls = []

        def validate(self, world, proposal, stage):
            self.calls.append(stage)
            return [GateIssue(code="blocked", message="test")] if stage == "approve" else []

    validator = Validator()
    world.validator = validator
    world.load_bundle(bundle)
    p = world.save_proposal(proposal(world))
    with pytest.raises(GateError, match="blocked"):
        world.approve(p.proposal_id, p.version, "Charles")
    assert validator.calls == ["save", "approve"]
    assert not world.history("CASE").approvals
    assert world.view("CASE").proposals[0].status == "proposed"


def test_decision_versioning_and_stale_basis_rejection(world, bundle):
    world.load_bundle(bundle)
    d = Decision(
        decision_id="D",
        case_id="CASE",
        version=99,
        evidence_set_hash=world.evidence_set_hash("CASE"),
        lines=[],
        current=True,
        model_id="stub",
        llm_mode="fake",
        prompt_version="stub",
        created_at=world.clock.now(),
    )
    first = world.save_decision(d)
    second = world.save_decision(d)
    assert (first.version, second.version) == (1, 2)
    assert first.decision_id != second.decision_id
    assert [d.current for d in world.history("CASE").decisions] == [False, True]
    world.confirm_field(doc(world).evidence_id, "signed", "Charles")
    with pytest.raises(GateError, match="stale_decision"):
        world.save_decision(d)


def test_line_reason_revisions_are_append_only_and_hash_changes(world, bundle):
    world.load_bundle(bundle)
    initial = world.evidence_set_hash("CASE")
    reason = world.set_line_reason("CASE", "U1", "shortage", FieldTrust.model_extracted, None)
    assert world.evidence_set_hash("CASE") != initial
    assert world.deduction_lines("CASE")[0].reason == "shortage"
    assert (
        world.set_line_reason("CASE", "U1", "shortage", FieldTrust.model_extracted, None) == reason
    )
    assert len(world.history("CASE").reasons) == 1


def test_nonpayment_and_zero_payment_deductions_never_make_np(world, bundle):
    bundle.docs = bundle.docs[:1]
    world.load_bundle(bundle)
    assert [line.line_id for line in world.deduction_lines("CASE")] == ["NP"]
    world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="REM",
            kind="remittance",
            title="Remit",
            fields={"ded.1.line_id": "D1", "ded.1.claimed_cents": 2000, "ded.1.reason": "shortage"},
        ),
    )
    assert [line.line_id for line in world.deduction_lines("CASE")] == ["D1", "U1"]


def test_persistence_clock_basis_and_due(tmp_path, bundle):
    parts = stub_parts()
    path = str(tmp_path / "world.db")
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    world.load_bundle(bundle)
    old = world.fact_set("CASE")
    work = DueWork(
        due_id="W",
        case_id="CASE",
        kind="recheck",
        due_at=world.clock.now() + timedelta(days=2),
        basis=old.basis_hash,
        idempotency_key="W",
    )
    world.schedule(work)
    assert world.schedule(work.model_copy(update={"due_id": "OTHER"})) == work
    world.advance_to(3, release_events=False)
    world.close()
    reopened = SqliteWorld(path, parts.ingestor, parts.validator)
    assert reopened.clock.day() == 3
    assert reopened.fact_set("CASE", old.basis_hash) == old
    assert reopened.due(reopened.clock.now()) == [work]
    assert reopened.next_due_day() == 3
    reopened.mark_due("W", "done")
    assert reopened.next_due_day() is None
    reopened.close()


def test_deduction_intake_uses_effective_facts_without_mutating_evidence(world, bundle):
    world.load_bundle(bundle)
    rem = world.add_evidence(
        "CASE",
        BundleDoc(
            doc_ref="REM",
            kind="remittance",
            title="Remit",
            fields={"ded.1.line_id": "D1", "ded.1.claimed_cents": 2000},
            text="Shortage",
        ),
    )
    world.add_fact(
        rem.evidence_id,
        "ded.1.reason",
        "shortage",
        FieldTrust.model_extracted,
        Citation(evidence_id=rem.evidence_id, locator="text", quote="Shortage"),
        "model",
    )
    assert world.deduction_lines("CASE")[0].reason == "shortage"
    assert world.deduction_lines("CASE")[0].reason_trust == "model_extracted"
    assert "ded.1.reason" not in world.evidence(rem.evidence_id).fields


def test_no_money_float_literals_or_annotations():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "recoup"
    for directory in (root / "contracts", root / "world"):
        for path in directory.rglob("*.py"):
            tree = ast.parse(path.read_text())
            assert not any(
                isinstance(node, ast.Constant) and isinstance(node.value, float)
                for node in ast.walk(tree)
            ), path
            assert not any(
                isinstance(node, ast.Name) and node.id == "float" for node in ast.walk(tree)
            ), path
