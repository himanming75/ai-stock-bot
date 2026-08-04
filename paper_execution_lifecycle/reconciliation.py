from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any


def _d(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except InvalidOperation:
        return Decimal("0")


def reconcile_positions(orders: list[dict], positions: list[dict]) -> dict:
    expected: dict[str, Decimal] = defaultdict(Decimal)

    for order in orders:
        status = str(order.get("status", "")).lower()
        if status not in {"filled", "partially_filled"}:
            continue
        qty = _d(order.get("filled_qty"))
        symbol = str(order.get("symbol", "")).upper()
        side = str(order.get("side", "")).lower()
        if not symbol:
            continue
        expected[symbol] += qty if side == "buy" else -qty

    actual = {
        str(position.get("symbol", "")).upper(): _d(position.get("qty"))
        for position in positions
        if position.get("symbol")
    }

    symbols = sorted(set(expected) | set(actual))
    differences = []
    for symbol in symbols:
        diff = actual.get(symbol, Decimal("0")) - expected.get(symbol, Decimal("0"))
        if diff != 0:
            differences.append({
                "symbol": symbol,
                "expected_qty_from_loaded_orders": str(expected.get(symbol, Decimal("0"))),
                "actual_position_qty": str(actual.get(symbol, Decimal("0"))),
                "difference": str(diff),
            })

    return {
        "matched": len(differences) == 0,
        "difference_count": len(differences),
        "differences": differences,
        "note": "Expected quantity is based only on orders returned in the current API window.",
    }


def reconcile_account(account: dict, positions: list[dict]) -> dict:
    equity = _d(account.get("equity"))
    cash = _d(account.get("cash"))
    market_value = sum((_d(item.get("market_value")) for item in positions), Decimal("0"))
    calculated = cash + market_value
    drift = equity - calculated

    return {
        "equity": str(equity),
        "cash": str(cash),
        "position_market_value": str(market_value),
        "calculated_equity": str(calculated),
        "equity_drift": str(drift),
        "within_tolerance": abs(drift) <= Decimal("1.00"),
        "tolerance": "1.00",
    }
