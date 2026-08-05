from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import OrderState, PositionState


def compare_order(
    expected: dict[str, Any],
    actual: OrderState,
) -> dict[str, Any]:
    checks = {
        "client_order_id_matches": (
            expected.get("client_order_id") == actual.client_order_id
        ),
        "symbol_matches": (
            str(expected.get("symbol", "")).upper() == actual.symbol
        ),
        "side_matches": (
            str(expected.get("side", "")).lower() == actual.side
        ),
        "status_known": actual.status in {
            "new", "accepted", "partially_filled", "filled",
            "canceled", "expired", "rejected",
        },
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "drift_detected": not all(checks.values()),
    }


def compare_positions(
    expected: list[PositionState],
    actual: list[PositionState],
) -> dict[str, Any]:
    expected_map = {item.symbol: item for item in expected}
    actual_map = {item.symbol: item for item in actual}
    symbols = sorted(set(expected_map) | set(actual_map))
    details = []
    drift = False

    for symbol in symbols:
        exp = expected_map.get(symbol)
        act = actual_map.get(symbol)
        exp_qty = exp.qty if exp else Decimal("0")
        act_qty = act.qty if act else Decimal("0")
        qty_match = exp_qty == act_qty
        drift = drift or not qty_match
        details.append({
            "symbol": symbol,
            "expected_qty": str(exp_qty),
            "actual_qty": str(act_qty),
            "qty_matches": qty_match,
        })

    return {
        "drift_detected": drift,
        "details": details,
    }


def compare_cash(
    *,
    expected_cash: Decimal,
    actual_cash: Decimal,
    expected_buying_power: Decimal,
    actual_buying_power: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> dict[str, Any]:
    cash_delta = actual_cash - expected_cash
    buying_power_delta = actual_buying_power - expected_buying_power
    checks = {
        "cash_within_tolerance": abs(cash_delta) <= tolerance,
        "buying_power_within_tolerance": (
            abs(buying_power_delta) <= tolerance
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "cash_delta": str(cash_delta),
        "buying_power_delta": str(buying_power_delta),
        "drift_detected": not all(checks.values()),
    }
