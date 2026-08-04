from __future__ import annotations
from typing import Any

def detect(market: dict[str, Any]) -> dict[str, Any]:
    trend = float(market.get("trend_score", 0) or 0)
    volatility = float(market.get("volatility_pct", 0) or 0)
    breadth = float(market.get("breadth_pct", 50) or 50)
    if volatility >= 4.0:
        regime = "HIGH_VOLATILITY"
    elif trend >= 60 and breadth >= 55:
        regime = "BULL_TREND"
    elif trend <= 40 and breadth <= 45:
        regime = "BEAR_TREND"
    else:
        regime = "SIDEWAYS"
    return {
        "regime": regime,
        "trend_score": trend,
        "volatility_pct": volatility,
        "breadth_pct": breadth,
    }
