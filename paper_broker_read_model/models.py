from __future__ import annotations
from typing import Any

def normalize_account(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash": float(snapshot.get("cash", 0.0)),
        "equity": float(snapshot.get("equity", 0.0)),
        "buying_power": float(snapshot.get("buying_power", 0.0)),
        "currency": str(snapshot.get("currency", "USD")),
        "status": str(snapshot.get("status", "UNKNOWN")),
    }

def normalize_positions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        output[symbol] = {
            "symbol": symbol,
            "quantity": float(row.get("quantity", 0.0)),
            "average_cost": float(row.get("average_cost", 0.0)),
            "market_price": float(row.get("market_price", 0.0)),
            "market_value": float(row.get("market_value", 0.0)),
            "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
        }
    return output

def internal_account_from_ledger(account_result: dict[str, Any]) -> dict[str, Any]:
    cash = float(
        account_result.get("cash_reconciliation", {}).get(
            "reported_ending_cash", 0.0
        )
    )
    equity = float(
        account_result.get("equity_reconciliation", {}).get(
            "reported_equity", 0.0
        )
    )
    return {
        "cash": cash,
        "equity": equity,
        "buying_power": cash,
        "currency": "USD",
        "status": "ACTIVE",
    }

def internal_positions_from_ledger(
    account_result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    rows = account_result.get("reported_positions", {})
    output: dict[str, dict[str, Any]] = {}
    for symbol, row in rows.items():
        if not isinstance(row, dict):
            continue
        normalized = str(symbol).upper()
        quantity = float(row.get("quantity", 0.0))
        average_cost = float(row.get("average_cost", 0.0))
        market_price = float(
            row.get("mark_price", row.get("market_price", average_cost))
        )
        reported_market_value = float(row.get("market_value", 0.0))
        calculated_market_value = quantity * market_price
        market_value = (
            reported_market_value
            if abs(reported_market_value) > 1e-12
            else calculated_market_value
        )
        output[normalized] = {
            "symbol": normalized,
            "quantity": quantity,
            "average_cost": average_cost,
            "market_price": market_price,
            "market_value": round(market_value, 6),
            "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
            "market_value_source": (
                "REPORTED"
                if abs(reported_market_value) > 1e-12
                else "CALCULATED_QUANTITY_X_MARK_PRICE"
            ),
        }
    return output
