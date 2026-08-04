from __future__ import annotations
from typing import Any


def build_context(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("governance", "account", "signal", "portfolio", "risk")
    missing = [name for name in required if not isinstance(payload.get(name), dict)]
    if missing:
        raise ValueError("MISSING_CONTEXT:" + ",".join(missing))

    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol:
        raise ValueError("SYMBOL_REQUIRED")

    return {
        "symbol": symbol,
        "governance": payload["governance"],
        "account": payload["account"],
        "positions": list(payload.get("positions", [])),
        "open_orders": list(payload.get("open_orders", [])),
        "signal": payload["signal"],
        "portfolio": payload["portfolio"],
        "risk": payload["risk"],
        "strategy_votes": list(payload.get("strategy_votes", [])),
    }
