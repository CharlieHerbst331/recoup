"""Contracts from design/02 §3.1."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from typing import Literal

from pydantic import BaseModel, Field

Currency = Literal["USD"]


class Money(BaseModel, frozen=True):
    cents: int = Field(strict=True)
    currency: Currency = "USD"


def parse_usd(text: str) -> Money:
    if not isinstance(text, str):
        raise ValueError("Expected USD text")
    cleaned = text.strip()
    if not re.fullmatch(r"[+-]?\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", cleaned):
        raise ValueError("Invalid USD amount")
    try:
        with localcontext() as ctx:
            ctx.prec = max(28, len(cleaned) + 4)
            dollars = Decimal(cleaned.replace("$", "").replace(",", ""))
            rounded = dollars.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            return Money(cents=int(rounded * 100))
    except InvalidOperation as exc:
        raise ValueError("Invalid USD amount") from exc


def bp_of(cents: int, bp: int) -> int:
    if type(cents) is not int or type(bp) is not int:
        raise ValueError("Cents and basis points must be integers")
    with localcontext() as ctx:
        ctx.prec = max(28, len(str(abs(cents))) + len(str(abs(bp))) + 4)
        return int(
            (Decimal(cents) * Decimal(bp) / Decimal(10000)).quantize(
                Decimal("1"), rounding=ROUND_HALF_EVEN
            )
        )


def clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(value, hi))


def fmt(m: Money) -> str:
    sign = "-" if m.cents < 0 else ""
    dollars, cents = divmod(abs(m.cents), 100)
    return f"{sign}${dollars:,}.{cents:02d}"
