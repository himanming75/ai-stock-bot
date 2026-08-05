from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def D(value: Any, default: Decimal = ZERO) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def text(value: Decimal) -> str:
    return format(value, "f")


def clamp(value: Decimal, low=ZERO, high=HUNDRED) -> Decimal:
    return min(high, max(low, value))
