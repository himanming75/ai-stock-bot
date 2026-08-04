from __future__ import annotations
from typing import Any

def normalize(value: dict[str, Any]) -> dict[str, Any]:
    bid = float(value.get("bid", 0) or 0)
    ask = float(value.get("ask", 0) or 0)
    last = float(value.get("last", 0) or 0)
    mid = round((bid + ask) / 2, 6) if bid > 0 and ask > 0 else last
    spread = max(0.0, ask - bid) if bid > 0 and ask > 0 else 0.0
    spread_pct = round(spread / mid * 100, 6) if mid > 0 else 0.0
    return {
        "symbol": str(value.get("symbol", "UNKNOWN")).upper(),
        "bid": bid,
        "ask": ask,
        "last": last,
        "mid": mid,
        "spread": round(spread, 6),
        "spread_pct": spread_pct,
        "quote_age_seconds": float(value.get("quote_age_seconds", 0) or 0),
        "market_open": value.get("market_open") is True,
        "average_daily_volume": int(value.get("average_daily_volume", 0) or 0),
    }
