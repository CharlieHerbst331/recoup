"""Contracts from design/02 §3.9."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .bundle import CaseBundle
from .models import GateIssue, LoadResult
from .money import Money


class RemittanceAllocation(BaseModel):
    invoice_no: str
    paid_cents: int = Field(strict=True, ge=0)


class RemittanceBundle(BaseModel):
    remittance_id: str
    version: int = Field(default=1, strict=True, ge=1)
    payment_ref: str
    buyer_id: str
    currency: str
    paid_cents: int = Field(strict=True, ge=0)
    paid_date: date
    cases: list[CaseBundle]
    allocations: list[RemittanceAllocation]


class CasePaymentAllocation(BaseModel):
    case_id: str
    invoice_no: str
    amount: Money


class RemittanceLoadResult(BaseModel):
    remittance_id: str
    version: int
    status: Literal["loaded", "needs_info", "needs_human", "quarantined"]
    results: list[LoadResult] = []
    allocations: list[CasePaymentAllocation] = []
    unapplied: Money | None = None
    issues: list[GateIssue] = []
    replay: bool = False
