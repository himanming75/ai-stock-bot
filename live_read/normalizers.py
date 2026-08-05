from __future__ import annotations
from typing import Any


def account(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(value.get("id", "")),
        "status": str(value.get("status", "")),
        "currency": str(value.get("currency", "")),
        "cash": str(value.get("cash", "0")),
        "buying_power": str(value.get("buying_power", "0")),
        "equity": str(value.get("equity", "0")),
        "trading_blocked": bool(value.get("trading_blocked", False)),
        "account_blocked": bool(value.get("account_blocked", False)),
    }


def positions(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "symbol": str(value.get("symbol", "")),
            "qty": str(value.get("qty", "0")),
            "market_value": str(value.get("market_value", "0")),
            "avg_entry_price": str(value.get("avg_entry_price", "0")),
            "unrealized_pl": str(value.get("unrealized_pl", "0")),
        }
        for value in values
    ]


def orders(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(value.get("id", "")),
            "client_order_id": str(value.get("client_order_id", "")),
            "symbol": str(value.get("symbol", "")),
            "side": str(value.get("side", "")),
            "type": str(value.get("type", "")),
            "status": str(value.get("status", "")),
            "qty": str(value.get("qty", "")),
            "notional": str(value.get("notional", "")),
        }
        for value in values
    ]


def clock(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "is_open": bool(value.get("is_open", False)),
        "timestamp": str(value.get("timestamp", "")),
        "next_open": str(value.get("next_open", "")),
        "next_close": str(value.get("next_close", "")),
    }


def asset(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(value.get("id", "")),
        "symbol": str(value.get("symbol", "")),
        "status": str(value.get("status", "")),
        "tradable": bool(value.get("tradable", False)),
        "fractionable": bool(value.get("fractionable", False)),
        "marginable": bool(value.get("marginable", False)),
        "shortable": bool(value.get("shortable", False)),
    }
