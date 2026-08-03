from __future__ import annotations
from typing import Any

def find_duplicate_fill_ids(fills: list[dict[str, Any]]) -> list[str]:
    seen = set()
    duplicates = []
    for row in fills:
        fill_id = str(row.get("fill_id") or "")
        if not fill_id:
            continue
        if fill_id in seen and fill_id not in duplicates:
            duplicates.append(fill_id)
        seen.add(fill_id)
    return duplicates

def reconcile_cash(
    cash_entries: list[dict[str, Any]],
    reported_ending_cash: float,
    tolerance: float,
) -> dict[str, Any]:
    calculated = sum(float(row.get("amount", 0.0)) for row in cash_entries)
    difference = calculated - reported_ending_cash
    return {
        "calculated_ending_cash": round(calculated, 4),
        "reported_ending_cash": round(reported_ending_cash, 4),
        "difference": round(difference, 4),
        "passed": abs(difference) <= tolerance,
    }

def reconcile_positions(
    calculated: dict[str, float],
    reported: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    symbols = sorted(set(calculated) | set(reported))
    details = {}
    passed = True
    for symbol in symbols:
        calc_qty = float(calculated.get(symbol, 0.0))
        reported_qty = float(
            reported.get(symbol, {}).get("quantity", 0.0)
            if isinstance(reported.get(symbol), dict)
            else reported.get(symbol, 0.0)
        )
        difference = calc_qty - reported_qty
        item_passed = abs(difference) <= tolerance
        details[symbol] = {
            "calculated_quantity": round(calc_qty, 6),
            "reported_quantity": round(reported_qty, 6),
            "difference": round(difference, 6),
            "passed": item_passed,
        }
        passed = passed and item_passed
    return {
        "passed": passed,
        "details": details,
    }

def reconcile_equity(
    ending_cash: float,
    market_value: float,
    reported_equity: float,
    tolerance: float,
) -> dict[str, Any]:
    calculated = ending_cash + market_value
    difference = calculated - reported_equity
    return {
        "calculated_equity": round(calculated, 4),
        "reported_equity": round(reported_equity, 4),
        "difference": round(difference, 4),
        "passed": abs(difference) <= tolerance,
    }
