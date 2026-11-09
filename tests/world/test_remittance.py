"""Historical remittance cash conservation, transaction and restart boundaries (§3.9)."""

from datetime import date

import pytest
from pydantic import ValidationError

from recoup.contracts.bundle import BundleDoc
from recoup.contracts.remittance import RemittanceAllocation, RemittanceBundle
from recoup.contracts.testing import stub_parts
from recoup.world import SqliteWorld


def case(bundle, identity="A", total=1000, buyer="BUYER"):
    return bundle.model_copy(
        update={
            "case_id": identity,
            "invoice_ref": f"INV-{identity}",
            "docs": [
                BundleDoc(
                    doc_ref=f"INV-{identity}",
                    kind="invoice",
                    title="SYNTHETIC invoice",
                    fields={
                        "invoice_no": f"INV-{identity}",
                        "buyer_id": buyer,
                        "total_cents": total,
                    },
                )
            ],
        }
    )


def remit(bundle, *, paid=2500, cases=None, allocations=None, **updates):
    data = dict(
        remittance_id="R",
        payment_ref="BANK",
        buyer_id="BUYER",
        currency="USD",
        paid_cents=paid,
        paid_date=date(2026, 10, 20),
        cases=cases if cases is not None else [case(bundle), case(bundle, "B")],
        allocations=allocations
        if allocations is not None
        else [
            RemittanceAllocation(invoice_no="INV-A", paid_cents=1200),
            RemittanceAllocation(invoice_no="INV-B", paid_cents=1000),
        ],
    )
    data.update(updates)
    return RemittanceBundle(**data)


def test_caps_balances_conserves_cash_and_records_allocated_evidence(world, bundle):
    source = remit(bundle)
    result = world.load_remittance(source)
    assert result.status == "loaded"
    assert [a.amount.cents for a in result.allocations] == [1000, 1000]
    assert result.unapplied.cents == 500
    assert sum(a.amount.cents for a in result.allocations) + result.unapplied.cents == 2500
    for identity in ["A", "B"]:
        assert world.ledger_balance(identity).cents == 0
        evidence = world.active_evidence(identity)
        assert next(e for e in evidence if e.kind == "payment").fields["paid_cents"] == 1000
        assert next(e for e in evidence if e.kind == "remittance").fields["paid_cents"] == 2500
        assert not world.history(identity).receipts
    before = world.db.total_changes
    assert world.load_remittance(source).replay
    assert world.db.total_changes == before
    assert world.remittance_history("R") == [result]


@pytest.mark.parametrize("problem", ["unmatched", "duplicate", "buyer", "ambiguous", "exceeds"])
def test_invalid_allocation_leaves_no_partial_cases_or_ledger(world, bundle, problem):
    source = remit(bundle)
    if problem == "unmatched":
        source.allocations[-1].invoice_no = "missing"
    elif problem == "duplicate":
        source.allocations[-1].invoice_no = "INV-A"
    elif problem == "buyer":
        source.cases[-1] = case(bundle, "B", buyer="OTHER")
    elif problem == "ambiguous":
        duplicate = case(bundle, "C")
        duplicate.docs[0].fields["invoice_no"] = "INV-A"
        source.cases.append(duplicate)
    else:
        source.paid_cents = 100

    class NoIngestion:
        def ingest(self, *args):
            raise AssertionError("Invalid references must fail before ingestion")

    world.ingestor = NoIngestion()
    result = world.load_remittance(source)
    assert result.status == "needs_info"
    assert result.unapplied.cents == source.paid_cents
    for table in ["cases", "ledger", "evidence", "events"]:
        assert world.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert world.remittance_history("R") == [result]


def test_currency_quarantines_entire_raw_bundle_before_money(world, bundle, monkeypatch):
    source = remit(bundle)
    source.cases[1].currency = "EUR"
    import recoup.world.remittance as module

    def forbidden(**kwargs):
        raise AssertionError("Quarantine cannot construct Money")

    monkeypatch.setattr(module, "Money", forbidden)
    result = world.load_remittance(source)
    assert result.status == "quarantined" and result.unapplied is None
    assert world.list_quarantined()[0].raw_bundle_json == source.model_dump_json()
    assert world.db.execute("SELECT count(*) FROM cases").fetchone()[0] == 0


def test_pending_revision_corrects_then_posted_revision_is_immutable(world, bundle):
    source = remit(bundle)
    source.allocations[0].invoice_no = "missing"
    assert world.load_remittance(source).status == "needs_info"
    corrected = remit(bundle, version=2)
    assert world.load_remittance(corrected).status == "loaded"
    before = [tuple(row) for row in world.db.execute("SELECT * FROM ledger")]
    assert world.load_remittance(remit(bundle, version=3)).status == "needs_human"
    conflict = remit(bundle, version=2, paid=3000)
    assert world.load_remittance(conflict).issues[0].code == "remittance_conflict"
    assert [tuple(row) for row in world.db.execute("SELECT * FROM ledger")] == before
    assert len(world.remittance_history("R")) == 4
    assert world.load_remittance(corrected).replay


def test_bank_identity_survives_restart_and_cannot_use_new_remittance_id(tmp_path, bundle):
    parts = stub_parts()
    path = str(tmp_path / "world.sqlite")
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    source = remit(bundle)
    world.load_remittance(source)
    world.close()
    world = SqliteWorld(path, parts.ingestor, parts.validator)
    assert world.load_remittance(source).replay
    duplicate = remit(bundle, remittance_id="OTHER")
    assert world.load_remittance(duplicate).status == "needs_human"
    assert world.ledger_balance("A").cents == 0
    assert len(world.remittance_history()) == 2
    world.close()


@pytest.mark.parametrize("attached", [False, True])
def test_preexisting_bank_cash_not_posted_twice(world, bundle, attached):
    child = case(bundle)
    payment = BundleDoc(
        doc_ref="DIRECT",
        kind="payment",
        title="SYNTHETIC bank payment",
        fields={"paid_cents": 100, "payment_ref": "BANK"},
    )
    if attached:
        world.load_bundle(child)
        world.add_evidence("A", payment)
    else:
        child.docs.append(payment)
    source = remit(
        bundle,
        cases=[child],
        allocations=[RemittanceAllocation(invoice_no="INV-A", paid_cents=500)],
    )
    before = [tuple(row) for row in world.db.execute("SELECT * FROM ledger")]
    result = world.load_remittance(source)
    assert result.status == "needs_info"
    assert result.issues[0].code == "payment_already_intaken"
    assert [tuple(row) for row in world.db.execute("SELECT * FROM ledger")] == before


def test_uses_current_canonical_invoice_evidence_and_rejects_stale_original_refs(world, bundle):
    child = case(bundle)
    world.load_bundle(child)
    replacement = child.docs[0].model_copy(
        update={
            "version": 2,
            "fields": {"invoice_no": "NEW", "buyer_id": "BUYER", "total_cents": 1000},
        }
    )
    world.add_evidence("A", replacement)
    stale = remit(
        bundle,
        cases=[child],
        allocations=[RemittanceAllocation(invoice_no="INV-A", paid_cents=500)],
    )
    assert world.load_remittance(stale).status == "needs_info"
    corrected = stale.model_copy(deep=True, update={"version": 2})
    corrected.allocations[0].invoice_no = "NEW"
    assert world.load_remittance(corrected).status == "loaded"
    assert world.ledger_balance("A").cents == 500


def test_mid_transaction_failure_rolls_back_all_children(world, bundle):
    original = world.add_evidence

    def fail_second(case_id, doc, bundle_dir=None):
        if case_id == "B" and doc.kind == "payment":
            raise RuntimeError("Injected storage failure")
        return original(case_id, doc, bundle_dir)

    world.add_evidence = fail_second
    with pytest.raises(RuntimeError, match="Injected"):
        world.load_remittance(remit(bundle))
    for table in ["cases", "ledger", "evidence", "events", "remittances"]:
        assert world.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    world.add_evidence = original
    assert world.load_remittance(remit(bundle)).status == "loaded"


@pytest.mark.parametrize("value", [True, 1.5, "10", -1])
def test_remittance_money_inputs_are_strict_nonnegative_integer_cents(value):
    with pytest.raises(ValidationError):
        RemittanceAllocation(invoice_no="INV", paid_cents=value)


def test_future_cash_and_blank_identity_fail_without_partial_cases(world, bundle):
    future = remit(bundle, paid_date=date(2026, 10, 21))
    assert world.load_remittance(future).issues[0].code == "future_payment"
    assert world.db.execute("SELECT count(*) FROM cases").fetchone()[0] == 0
    blank = remit(bundle, remittance_id="", payment_ref="", version=2)
    assert world.load_remittance(blank).issues[0].code == "missing_identity"
    assert world.db.execute("SELECT count(*) FROM cases").fetchone()[0] == 0


def test_new_clock_uses_child_start_date_for_historical_cash(world, bundle):
    children = [case(bundle), case(bundle, "B")]
    for child in children:
        child.start_date = date(2027, 1, 1)
    source = remit(bundle, cases=children, paid_date=date(2027, 1, 1))
    assert world.load_remittance(source).status == "loaded"
    assert world.clock.now().date() == date(2027, 1, 1)


def test_unallocated_revision_can_correct_but_cannot_change_bank_identity(world, bundle):
    source = remit(bundle, paid=1000, allocations=[])
    assert world.load_remittance(source).unapplied.cents == 1000
    changed = remit(bundle, version=2, payment_ref="DIFFERENT")
    assert world.load_remittance(changed).issues[0].code == "remittance_bank_identity"
    corrected = remit(
        bundle,
        version=3,
        paid=1000,
        allocations=[RemittanceAllocation(invoice_no="INV-A", paid_cents=1000)],
    )
    assert world.load_remittance(corrected).status == "loaded"


def test_non_usd_conflicting_revision_quarantines_without_changing_original(world, bundle):
    original = remit(bundle)
    world.load_remittance(original)
    changed = remit(bundle, currency="EUR")
    assert world.load_remittance(changed).status == "quarantined"
    assert world.load_remittance(original).replay
    assert world.ledger_balance("A").cents == 0


def test_reserved_evidence_collision_rolls_back_allocations_and_case_intake(world, bundle):
    child = case(bundle)
    child.docs.append(
        BundleDoc(
            doc_ref="remittance:R",
            kind="other",
            title="Existing source",
            text="Unrelated original evidence",
        )
    )
    source = remit(
        bundle,
        cases=[child],
        allocations=[RemittanceAllocation(invoice_no="INV-A", paid_cents=1000)],
    )
    result = world.load_remittance(source)
    assert result.status == "needs_info"
    assert result.issues[0].code == "remittance_evidence_conflict"
    assert world.db.execute("SELECT count(*) FROM cases").fetchone()[0] == 0


def test_zero_balance_audit_can_be_superseded_before_any_cash_posts(world, bundle):
    child = case(bundle)
    child.docs.append(
        BundleDoc(
            doc_ref="PRIOR-CASH",
            kind="payment",
            title="Other bank cash",
            fields={"paid_cents": 1000, "payment_ref": "OTHER"},
        )
    )
    source = remit(
        bundle,
        paid=500,
        cases=[child],
        allocations=[RemittanceAllocation(invoice_no="INV-A", paid_cents=500)],
    )
    result = world.load_remittance(source)
    assert result.status == "loaded" and not result.allocations
    assert result.unapplied.cents == 500
    audit = next(e for e in world.active_evidence("A") if e.kind == "remittance")
    revised = source.model_copy(update={"version": 2})
    assert world.load_remittance(revised).status == "loaded"
    assert not world.evidence(audit.evidence_id).active
    assert world.ledger_balance("A").cents == 0


def test_rejected_lower_revision_cannot_redefine_original_bank_identity(world, bundle):
    initial = remit(bundle, version=2, allocations=[])
    assert world.load_remittance(initial).status == "loaded"
    rejected = remit(bundle, version=1, payment_ref="OTHER")
    assert world.load_remittance(rejected).issues[0].code == "remittance_bank_identity"
    assert world.load_remittance(remit(bundle, version=3)).status == "loaded"
