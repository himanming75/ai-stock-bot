from __future__ import annotations
from typing import Any

def translate_account(account: dict[str, Any]) -> dict[str, Any]:
    return {
        "cash": float(account.get("cash", 0.0)),
        "equity": float(account.get("equity", 0.0)),
        "buying_power": float(account.get("buying_power", 0.0)),
        "currency": str(account.get("currency", "USD")),
        "status": str(account.get("status", "UNKNOWN")),
    }

def translate_position(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(position.get("symbol", "")),
        "quantity": float(position.get("quantity", 0.0)),
        "average_cost": float(position.get("average_cost", 0.0)),
        "market_price": float(position.get("market_price", 0.0)),
        "market_value": float(position.get("market_value", 0.0)),
        "unrealized_pnl": float(position.get("unrealized_pnl", 0.0)),
    }

def translate_order_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(plan.get("symbol", "")),
        "side": str(plan.get("side", "")).upper(),
        "quantity": float(plan.get("quantity", 0.0)),
        "order_type": str(plan.get("order_type", "MARKET_SIMULATION_ONLY")),
        "time_in_force": str(plan.get("time_in_force", "DAY")),
        "submission_allowed": False,
    }

def translate_fill(fill: dict[str, Any]) -> dict[str, Any]:
    return {
        "fill_id": str(fill.get("fill_id", "")),
        "symbol": str(fill.get("symbol", "")),
        "side": str(fill.get("side", "")).upper(),
        "filled_quantity": float(fill.get("filled_quantity", 0.0)),
        "fill_price": float(fill.get("fill_price", 0.0)),
        "commission": float(fill.get("commission", 0.0)),
        "simulated": True,
    }
