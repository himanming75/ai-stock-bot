from __future__ import annotations
from typing import Any

def position_multiplier(
    consensus: dict[str, Any],
    base_multiplier: float,
) -> float:
    multiplier = float(base_multiplier)
    if consensus.get("conflict_detected"):
        multiplier *= 0.5
    if consensus.get("risk_mode") == "RISK_OFF":
        multiplier *= 0.7
    if consensus.get("volatility_regime") == "HIGH_VOLATILITY":
        multiplier *= 0.6
    elif consensus.get("volatility_regime") == "NORMAL_VOLATILITY":
        multiplier *= 0.85

    alignment = float(consensus.get("alignment_pct", 0.0))
    if alignment >= 100:
        multiplier *= 1.0
    elif alignment >= 67:
        multiplier *= 0.9
    else:
        multiplier *= 0.7

    return round(max(0.0, min(1.0, multiplier)), 4)

def recommend_strategies(
    consensus: dict[str, Any],
    base_recommendations: list[str],
) -> list[str]:
    primary = consensus.get("primary_regime")
    preferred = {
        "BULL": ["MOMENTUM", "EMA_CROSS", "MACD"],
        "BEAR": ["RSI", "BOLLINGER"],
        "SIDEWAYS": ["RSI", "BOLLINGER", "MACD"],
    }.get(primary, [])

    ordered = [name for name in preferred if name in base_recommendations]
    ordered += [name for name in base_recommendations if name not in ordered]
    return ordered[:3]
