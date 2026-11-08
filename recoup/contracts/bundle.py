"""Contracts from design/02 §3.3."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .models import DocKind, Scalar


class BundleDoc(BaseModel):
    doc_ref: str
    version: int = 1
    kind: DocKind
    title: str
    file: str | None = None
    text: str = ""
    fields: dict[str, Scalar] = {}
    available_at_day: int = 0
    held_by: Literal["erp", "shipping", "email", "insurer"] | None = None


class BundleEvent(BaseModel):
    at_day: int
    type: Literal["add_doc"]
    doc: BundleDoc


class CaseBundle(BaseModel):
    case_id: str
    title: str
    seller: str
    buyer: str
    currency: str
    invoice_ref: str
    start_date: date
    static_day: int = 0
    policy_ref: str | None = None
    allowed_recipients: dict[str, list[str]] = {}
    docs: list[BundleDoc]
    events: list[BundleEvent] = []
    provenance: Literal["synthetic"] = "synthetic"
