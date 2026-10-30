"""Currency-safe monetary helpers (no float comparisons)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MONEY_QUANTUM = Decimal("0.01")


def to_money(value) -> Decimal:
    """Parse a money value to two-decimal Decimal. Raises InvalidOperation/ValueError."""
    if value is None:
        raise InvalidOperation("amount is required")
    if isinstance(value, Decimal):
        d = value
    else:
        d = Decimal(str(value).strip())
    return d.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def amounts_equal(left, right) -> bool:
    try:
        return to_money(left) == to_money(right)
    except (InvalidOperation, ValueError, TypeError, ArithmeticError):
        return False


def normalize_currency(code, *, default="BDT") -> str:
    raw = (code or default or "BDT").strip().upper()
    return raw or default
