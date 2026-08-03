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
        output[normalized] = {
            "symbol": normalized,
            "quantity": float(row.get("quantity", 0.0)),
            "average_cost": float(row.get("average_cost", 0.0)),
            "market_price": float(row.get("mark_price", row.get("average_cost", 0.0))),
            "market_value": float(row.get("market_value", 0.0)),
            "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
        }
    return output
