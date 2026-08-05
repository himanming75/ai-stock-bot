from __future__ import annotations
from decimal import Decimal
from typing import Any


def position_map(values: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(value.get("symbol", "")).upper(): dict(value)
        for value in values
        if str(value.get("symbol", "")).strip()
    }


def compare_positions(
    broker_positions: list[dict[str, Any]],
    local_positions: list[dict[str, Any]],
    tolerance: Decimal,
) -> list[dict[str, Any]]:
    broker = position_map(broker_positions)
    local = position_map(local_positions)
    symbols = sorted(set(broker) | set(local))
    drifts = []

    for symbol in symbols:
        broker_qty = Decimal(str(broker.get(symbol, {}).get("qty", "0")))
        local_qty = Decimal(str(local.get(symbol, {}).get("qty", "0")))
        difference = broker_qty - local_qty
        if abs(difference) > tolerance:
            drifts.append({
                "type": "POSITION_QTY_DRIFT",
                "symbol": symbol,
                "broker_qty": str(broker_qty),
                "local_qty": str(local_qty),
                "difference": str(difference),
            })
    return drifts


def compare_account(
    broker_account: dict[str, Any],
    local_portfolio: dict[str, Any],
    tolerance: Decimal,
) -> list[dict[str, Any]]:
    drifts = []
    pairs = [
        ("cash", broker_account.get("cash", "0"), local_portfolio.get("cash", "0")),
        ("equity", broker_account.get("equity", "0"), local_portfolio.get("equity", "0")),
    ]
    for field, broker_value, local_value in pairs:
        broker_decimal = Decimal(str(broker_value))
        local_decimal = Decimal(str(local_value))
        difference = broker_decimal - local_decimal
        if abs(difference) > tolerance:
            drifts.append({
                "type": "ACCOUNT_VALUE_DRIFT",
                "field": field,
                "broker_value": str(broker_decimal),
                "local_value": str(local_decimal),
                "difference": str(difference),
            })
    return drifts
