from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        return Decimal("0")


def compare_accounts(previous: dict, current: dict, tolerance: Decimal) -> list[dict]:
    fields = ("cash", "equity", "portfolio_value", "buying_power")
    drifts = []
    for field in fields:
        old = _d(previous.get(field))
        new = _d(current.get(field))
        difference = new - old
        if abs(difference) > tolerance:
            drifts.append({
                "type": "ACCOUNT_VALUE_DRIFT",
                "field": field,
                "previous": str(old),
                "current": str(new),
                "difference": str(difference),
            })
    return drifts


def compare_positions(previous: list[dict], current: list[dict], tolerance: Decimal) -> list[dict]:
    old_map = {item["symbol"]: item for item in previous if item.get("symbol")}
    new_map = {item["symbol"]: item for item in current if item.get("symbol")}
    drifts = []

    for symbol in sorted(set(old_map) | set(new_map)):
        old = old_map.get(symbol)
        new = new_map.get(symbol)

        if old is None:
            drifts.append({
                "type": "POSITION_DISCOVERED",
                "symbol": symbol,
                "previous_qty": "0",
                "current_qty": str(new.get("qty", "0")),
            })
            continue

        if new is None:
            drifts.append({
                "type": "POSITION_MISSING",
                "symbol": symbol,
                "previous_qty": str(old.get("qty", "0")),
                "current_qty": "0",
            })
            continue

        old_qty = _d(old.get("qty"))
        new_qty = _d(new.get("qty"))
        if abs(new_qty - old_qty) > tolerance:
            drifts.append({
                "type": "POSITION_QTY_DRIFT",
                "symbol": symbol,
                "previous_qty": str(old_qty),
                "current_qty": str(new_qty),
                "difference": str(new_qty - old_qty),
            })

    return drifts
