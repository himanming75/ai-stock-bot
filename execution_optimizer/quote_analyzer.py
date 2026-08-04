from __future__ import annotations
from typing import Any

def analyze(quote: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    bid = float(quote.get("bid", 0) or 0)
    ask = float(quote.get("ask", 0) or 0)
    last = float(quote.get("last", 0) or 0)
    age = float(quote.get("quote_age_seconds", 0) or 0)
    mid = (bid + ask) / 2 if bid > 0 and ask > 0 else last
    spread = ask - bid if ask >= bid > 0 else 0.0
    spread_pct = spread / mid * 100 if mid > 0 else 0.0
    locked = bid > 0 and ask > 0 and bid == ask
    crossed = bid > ask > 0
    checks = {
        "positive_quote": bid > 0 and ask > 0,
        "not_crossed": not crossed,
        "fresh": age <= float(policy["maximum_quote_age_seconds"]),
        "spread_within_limit": spread_pct <= float(policy["maximum_spread_pct"]),
    }
    return {
        "bid": bid, "ask": ask, "last": last, "mid": round(mid, 6),
        "spread": round(spread, 6), "spread_pct": round(spread_pct, 6),
        "quote_age_seconds": age, "locked": locked, "crossed": crossed,
        "checks": checks, "passed": all(checks.values()),
    }
