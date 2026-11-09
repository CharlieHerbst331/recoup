import inspect
import types
from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal, Union, get_args, get_origin

import pytest
from pydantic import BaseModel

from recoup.contracts import bundle, interfaces, models, money, oracle, remittance, tools
from recoup.contracts.testing import stub_parts

MODULES = (money, models, bundle, tools, interfaces, oracle, remittance)
MODEL_TYPES = [
    cls
    for module in MODULES
    for _, cls in inspect.getmembers(module, inspect.isclass)
    if issubclass(cls, BaseModel) and cls.__module__ == module.__name__
]


def specimen(annotation):
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is interfaces.EngineParts:
        return stub_parts()
    if origin in (Union, types.UnionType):
        return specimen(next(arg for arg in args if arg is not type(None)))
    if origin is Literal:
        return args[0]
    if origin is list:
        return [specimen(args[0])]
    if origin is dict:
        return {specimen(args[0]): specimen(args[1])}
    if origin is tuple:
        return tuple(specimen(arg) for arg in args)
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        return next(iter(annotation))
    if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
        return annotation(
            **{name: specimen(field.annotation) for name, field in annotation.model_fields.items()}
        )
    if annotation is datetime:
        return datetime(2026, 10, 20, tzinfo=timezone.utc)
    if annotation is date:
        return date(2026, 10, 20)
    return {str: "sample", int: 1, bool: True, type(None): None, dict: {"sample": "value"}}[
        annotation
    ]


@pytest.mark.parametrize("cls", MODEL_TYPES, ids=lambda cls: cls.__name__)
def test_every_model_round_trip(cls):
    value = specimen(cls)
    if cls is interfaces.EngineParts:
        # Ports contain Python objects, not JSON wire models.
        restored = cls.model_validate(value.model_dump())
        assert restored.engine is value.engine
        assert restored.ingestor is value.ingestor
        assert restored.validator is value.validator
        assert restored.tools is value.tools
    else:
        restored = cls.model_validate_json(value.model_dump_json())
        assert restored == value
        assert cls.model_json_schema()["type"] == "object"


def test_mutable_defaults_are_independent():
    a = models.LoadResult(case_id="A", status="loaded")
    b = models.LoadResult(case_id="B", status="loaded")
    assert a.reason == b.reason == ""
    doc_a = bundle.BundleDoc(doc_ref="a", kind="invoice", title="A")
    doc_b = bundle.BundleDoc(doc_ref="b", kind="invoice", title="B")
    doc_a.fields["total_cents"] = 100
    assert doc_b.fields == {}
    envelope_a = tools.ToolEnvelope(ok=True, result={})
    envelope_b = tools.ToolEnvelope(ok=True, result={})
    envelope_a.issues.append(models.GateIssue(code="a", message="a"))
    assert envelope_b.issues == []


def test_money_target_and_insurer_contracts():
    assert set(models.KIND_TARGET) == set(models.ProposalKind)
    assert models.KIND_TARGET[models.ProposalKind.correction] == models.Target.mock_buyer_portal
    assert models.KIND_TARGET[models.ProposalKind.credit_memo] == models.Target.mock_erp
    assert models.KIND_TARGET[models.ProposalKind.claim_package] == models.Target.mock_insurer
    assert not {"coverage", "eligibility", "payout"} & set(models.Readiness.model_fields)
    assert "amount" not in tools.ProposeDecisionArgs.model_fields
    assert "amount" not in tools.DraftProposalArgs.model_fields
    assert "case_id" not in tools.ListEvidenceArgs.model_fields
    assert "Money" not in str(models.QuarantineRecord.model_fields)
    assert (
        bundle.CaseBundle.model_validate(
            {**specimen(bundle.CaseBundle).model_dump(), "currency": "EUR"}
        ).currency
        == "EUR"
    )


@pytest.mark.parametrize("value", ["text", 100, True, False, None])
def test_scalar_json_types_survive(value):
    args = tools.ProposeFactArgs(
        evidence_id="EV-H-POD-v1",
        key="signed",
        value=value,
        citation=models.Citation(evidence_id="EV-H-POD-v1", locator="text", quote="signed"),
    )
    restored = tools.ProposeFactArgs.model_validate_json(args.model_dump_json())
    assert type(restored.value) is type(value)
    assert restored.value == value
