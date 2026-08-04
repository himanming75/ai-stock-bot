from __future__ import annotations
from typing import Any

def account(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": value.get("id"),
        "status": value.get("status"),
        "cash": value.get("cash"),
        "equity": value.get("equity"),
        "last_equity": value.get("last_equity"),
        "buying_power": value.get("buying_power"),
        "portfolio_value": value.get("portfolio_value"),
        "daytrade_count": value.get("daytrade_count"),
        "pattern_day_trader": value.get("pattern_day_trader"),
        "trading_blocked": value.get("trading_blocked"),
        "account_blocked": value.get("account_blocked"),
    }

def position(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": value.get("asset_id"),
        "symbol": value.get("symbol"),
        "side": value.get("side"),
        "qty": value.get("qty"),
        "avg_entry_price": value.get("avg_entry_price"),
        "current_price": value.get("current_price"),
        "market_value": value.get("market_value"),
        "cost_basis": value.get("cost_basis"),
        "unrealized_pl": value.get("unrealized_pl"),
        "unrealized_plpc": value.get("unrealized_plpc"),
        "change_today": value.get("change_today"),
    }

def order(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": value.get("id"),
        "client_order_id": value.get("client_order_id"),
        "symbol": value.get("symbol"),
        "side": value.get("side"),
        "type": value.get("type"),
        "time_in_force": value.get("time_in_force"),
        "status": value.get("status"),
        "qty": value.get("qty"),
        "notional": value.get("notional"),
        "filled_qty": value.get("filled_qty"),
        "filled_avg_price": value.get("filled_avg_price"),
        "submitted_at": value.get("submitted_at"),
        "filled_at": value.get("filled_at"),
        "canceled_at": value.get("canceled_at"),
        "failed_at": value.get("failed_at"),
    }
