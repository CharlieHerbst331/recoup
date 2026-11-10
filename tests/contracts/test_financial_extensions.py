"""Financial wire contracts from design/02 §3.9 and §5.4."""

from datetime import date

import pytest
from pydantic import ValidationError

from recoup.contracts.bundle import CaseBundle
from recoup.contracts.models import Approval, FactSet, GateIssue, Proposal, Receipt
from recoup.contracts.money import Money
from recoup.contracts.remittance import (
    CasePaymentAllocation,
    RemittanceAllocation,
    RemittanceBundle,
    RemittanceLoadResult,
)
from recoup.contracts.tools import DraftProposalArgs, tool_json_schemas


def remittance_payload(currency="USD"):
    return {
        "remittance_id": "REM-1",
        "payment_ref": "BANK-1",
        "buyer_id": "BUYER-1",
        "currency": currency,
        "paid_cents": 12_345,
        "paid_date": "2026-11-09",
        "cases": [
            CaseBundle(
                case_id="INV-1",
                title="SYNTHETIC invoice",
                seller="Seller",
                buyer="Buyer",
                currency=currency,
                invoice_ref="invoice",
                start_date=date(2026, 11, 9),
                docs=[],
            ).model_dump(mode="json")
        ],
        "allocations": [{"invoice_no": "INV-1", "paid_cents": 12_345}],
    }


@pytest.mark.parametrize("currency", ["USD", "EUR"])
def test_remittance_input_preserves_raw_currency_without_money(currency):
    value = RemittanceBundle.model_validate(remittance_payload(currency))
    assert value.currency == value.cases[0].currency == currency
    assert value.version == 1
    assert value.paid_cents == value.allocations[0].paid_cents == 12_345
    assert RemittanceBundle.model_validate_json(value.model_dump_json()) == value
    assert "Money" not in RemittanceBundle.model_json_schema()["$defs"]


@pytest.mark.parametrize("bad", [-1, 1.5, 1.0, "100", True, False, None])
def test_remittance_money_is_strict_nonnegative_integer(bad):
    with pytest.raises(ValidationError):
        RemittanceBundle.model_validate({**remittance_payload(), "paid_cents": bad})
    with pytest.raises(ValidationError):
        RemittanceAllocation(invoice_no="INV-1", paid_cents=bad)


@pytest.mark.parametrize("bad", [0, -1, True, "2", 1.0])
def test_remittance_revision_is_strict_positive_integer(bad):
    with pytest.raises(ValidationError):
        RemittanceBundle.model_validate({**remittance_payload(), "version": bad})


def test_remittance_result_round_trip_and_independent_defaults():
    allocation = CasePaymentAllocation(
        case_id="CASE-1", invoice_no="INV-1", amount=Money(cents=12_000)
    )
    result = RemittanceLoadResult(
        remittance_id="REM-1",
        version=1,
        status="loaded",
        allocations=[allocation],
        unapplied=Money(cents=345),
    )
    assert RemittanceLoadResult.model_validate_json(result.model_dump_json()) == result
    assert sum(row.amount.cents for row in result.allocations) + result.unapplied.cents == 12_345
    other = RemittanceLoadResult(remittance_id="REM-2", version=1, status="quarantined")
    assert other.unapplied is None
    result.issues.append(GateIssue(code="example", message="example"))
    assert other.issues == []


def test_offer_reference_defaults_preserve_existing_wire_payloads():
    for cls in (Proposal, Approval, Receipt, DraftProposalArgs):
        field = cls.model_fields["offer_ref"]
        assert field.default is None
        assert not field.is_required()
    args = DraftProposalArgs(
        kind="counteroffer",
        line_ids=["D1"],
        recipient="buyer@example.test",
        draft_text="SYNTHETIC MOCK offer",
        citations=[],
        offer_ref="BUYER:offer/1",
    )
    assert DraftProposalArgs.model_validate_json(args.model_dump_json()) == args
    assert (
        DraftProposalArgs.model_validate({**args.model_dump(), "offer_ref": None}).offer_ref is None
    )
    schema = next(row for row in tool_json_schemas() if row["name"] == "draft_proposal")
    assert "offer_ref" in schema["parameters"]["properties"]
    assert not {"amount", "amount_cents", "allocations"} & set(schema["parameters"]["properties"])


def test_factset_buyer_sender_scope_is_additive_and_round_trips():
    old = {"case_id": "A", "basis_hash": "basis", "facts": [], "docs": []}
    a = FactSet.model_validate(old)
    b = FactSet.model_validate(old)
    assert a.buyer_senders == []
    a.buyer_senders.append("buyer@example.test")
    assert b.buyer_senders == []
    assert FactSet.model_validate_json(a.model_dump_json()) == a
