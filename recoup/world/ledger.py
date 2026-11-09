"""Integer ledger helpers (design/02 §3.7)."""

from recoup.contracts.models import LedgerEntry
from recoup.contracts.money import Money


def balance(entries: list[LedgerEntry]) -> Money:
    return Money(cents=sum(e.amount.cents * (1 if e.kind == "invoice" else -1) for e in entries))


def cents(fields: dict, key: str, default: int = 0) -> int:
    value = fields.get(key, default)
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} must be nonnegative integer cents")
    return value
