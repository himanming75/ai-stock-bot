from __future__ import annotations
from typing import Any


def account(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(value.get("id", "")),
        "status": str(value.get("status", "")),
        "currency": str(value.get("currency", "USD")),
        "cash": str(value.get("cash", "0")),
        "portfolio_value": str(value.get("portfolio_value", "0")),
        "equity": str(value.get("equity", "0")),
        "buying_power": str(value.get("buying_power", "0")),
        "trading_blocked": bool(value.get("trading_blocked", False)),
        "account_blocked": bool(value.get("account_blocked", False)),
        "pattern_day_trader": bool(value.get("pattern_day_trader", False)),
    }


def positions(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for value in values:
        result.append({
            "asset_id": str(value.get("asset_id", "")),
            "symbol": str(value.get("symbol", "")).upper(),
            "exchange": str(value.get("exchange", "")),
            "asset_class": str(value.get("asset_class", "")),
            "qty": str(value.get("qty", "0")),
            "side": str(value.get("side", "")),
            "market_value": str(value.get("market_value", "0")),
            "cost_basis": str(value.get("cost_basis", "0")),
            "avg_entry_price": str(value.get("avg_entry_price", "0")),
            "current_price": str(value.get("current_price", "0")),
            "unrealized_pl": str(value.get("unrealized_pl", "0")),
        })
    return sorted(result, key=lambda item: item["symbol"])


def orders(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for value in values:
        result.append({
            "id": str(value.get("id", "")),
            "client_order_id": str(value.get("client_order_id", "")),
            "symbol": str(value.get("symbol", "")).upper(),
            "side": str(value.get("side", "")),
            "type": str(value.get("type", "")),
            "status": str(value.get("status", "")),
            "qty": str(value.get("qty", "")),
            "notional": str(value.get("notional", "")),
            "filled_qty": str(value.get("filled_qty", "0")),
            "limit_price": str(value.get("limit_price", "")),
            "submitted_at": str(value.get("submitted_at", "")),
        })
    return sorted(result, key=lambda item: (item["symbol"], item["id"]))


def clock(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": str(value.get("timestamp", "")),
        "is_open": bool(value.get("is_open", False)),
        "next_open": str(value.get("next_open", "")),
        "next_close": str(value.get("next_close", "")),
    }


def asset(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(value.get("id", "")),
        "symbol": str(value.get("symbol", "")).upper(),
        "name": str(value.get("name", "")),
        "exchange": str(value.get("exchange", "")),
        "asset_class": str(value.get("class", value.get("asset_class", ""))),
        "status": str(value.get("status", "")),
        "tradable": bool(value.get("tradable", False)),
        "marginable": bool(value.get("marginable", False)),
        "shortable": bool(value.get("shortable", False)),
        "easy_to_borrow": bool(value.get("easy_to_borrow", False)),
        "fractionable": bool(value.get("fractionable", False)),
    }
