from __future__ import annotations


def account(value: dict) -> dict:
    return {
        "status": value.get("status"),
        "cash": str(value.get("cash", "0")),
        "equity": str(value.get("equity", "0")),
        "last_equity": str(value.get("last_equity", "0")),
        "portfolio_value": str(value.get("portfolio_value", "0")),
        "buying_power": str(value.get("buying_power", "0")),
        "account_blocked": bool(value.get("account_blocked", False)),
        "trading_blocked": bool(value.get("trading_blocked", False)),
    }


def position(value: dict) -> dict:
    return {
        "symbol": str(value.get("symbol", "")).upper(),
        "qty": str(value.get("qty", "0")),
        "avg_entry_price": str(value.get("avg_entry_price", "0")),
        "market_value": str(value.get("market_value", "0")),
        "cost_basis": str(value.get("cost_basis", "0")),
        "unrealized_pl": str(value.get("unrealized_pl", "0")),
        "side": str(value.get("side", "")),
    }
