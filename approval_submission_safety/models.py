from __future__ import annotations
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

ZERO = Decimal("0")


def D(value: Any, default: Decimal = ZERO) -> Decimal:
    try:
        if value is None or value == "":
            return default
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default


def parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
