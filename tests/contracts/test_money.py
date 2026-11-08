import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from recoup.contracts.money import Money, bp_of, clamp, fmt, parse_usd


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("$1,234.50", 123450),
        ("0", 0),
        (" 12.00 ", 1200),
        ("1.005", 100),
        ("1.015", 102),
        ("1.025", 102),
        ("1.035", 104),
        ("-1.005", -100),
        ("-1.015", -102),
        ("999999999999999999999999999999.995", 100000000000000000000000000000000),
    ],
)
def test_parse_usd_half_even(text, cents):
    assert parse_usd(text) == Money(cents=cents)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "NaN",
        "Infinity",
        "1e3",
        "1,23.45",
        "12,345,67",
        "EUR 1.00",
        "$$1",
        "1.00 USD",
        "1 000",
        None,
    ],
)
def test_parse_usd_invalid(text):
    with pytest.raises(ValueError):
        parse_usd(text)


@pytest.mark.parametrize(
    ("cents", "bp", "expected"),
    [
        (1, 5000, 0),
        (3, 5000, 2),
        (5, 5000, 2),
        (7, 5000, 4),
        (-1, 5000, 0),
        (-3, 5000, -2),
        (101, 10000, 101),
        (123450, 250, 3086),
        (10**40 + 3, 5000, 5 * 10**39 + 2),
    ],
)
def test_bp_of_half_even(cents, bp, expected):
    assert bp_of(cents, bp) == expected


def test_integer_money_currency_and_freezing():
    for value in [1.0, 1.5, True, "100"]:
        with pytest.raises(ValidationError):
            Money(cents=value)
    with pytest.raises(ValidationError):
        Money(cents=100, currency="EUR")
    money = Money(cents=10)
    with pytest.raises(ValidationError):
        money.cents = 20
    with pytest.raises(ValueError):
        bp_of(1.0, 100)


def test_fmt_and_clamp():
    assert fmt(Money(cents=123450)) == "$1,234.50"
    assert fmt(Money(cents=-105)) == "-$1.05"
    assert fmt(Money(cents=0)) == "$0.00"
    assert [clamp(x, 1, 60) for x in [0, 1, 10, 60, 61]] == [1, 1, 10, 60, 60]


def test_no_float_money_in_contracts_or_world():
    root = Path(__file__).resolve().parents[2] / "recoup"
    for area in ["contracts", "world"]:
        for path in (root / area).rglob("*.py"):
            tree = ast.parse(path.read_text())
            assert not any(
                (isinstance(node, ast.Constant) and isinstance(node.value, float))
                or (isinstance(node, ast.Name) and node.id == "float")
                for node in ast.walk(tree)
            ), path
