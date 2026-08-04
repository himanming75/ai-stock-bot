from __future__ import annotations
from typing import Any

def estimate(quote: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    spread_pct = float(quote.get("spread_pct", 0) or 0)
    volume_ratio = float(market.get("relative_volume", 1) or 1)
    depth = float(market.get("top_of_book_depth", 0) or 0)
    volatility = float(market.get("volatility_pct", 0) or 0)
    score = 85.0
    score -= min(40.0, spread_pct * 80)
    score += min(10.0, max(0.0, volume_ratio - 1) * 10)
    score += min(5.0, depth / 1000)
    score -= min(20.0, volatility * 3)
    return {"fill_probability_pct": round(max(0.0, min(100.0, score)), 4)}
