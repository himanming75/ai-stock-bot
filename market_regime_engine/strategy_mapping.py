from __future__ import annotations
from typing import Any

DEFAULT_MAPPING = {
    "BULL": ["MOMENTUM", "EMA_CROSS", "MACD"],
    "BEAR": ["RSI", "BOLLINGER"],
    "SIDEWAYS": ["RSI", "BOLLINGER"],
}

def recommend_strategies(
    regime: dict[str, Any],
    available: list[str],
) -> list[str]:
    preferred = DEFAULT_MAPPING.get(
        regime.get("primary_regime", "SIDEWAYS"),
        [],
    )
    selected = [name for name in preferred if name in available]
    if not selected:
        selected = available[:3]
    return selected

def position_multiplier(regime: dict[str, Any]) -> float:
    primary = regime.get("primary_regime")
    vol = regime.get("volatility_regime")
    risk_mode = regime.get("risk_mode")

    multiplier = 1.0
    if primary == "BULL":
        multiplier *= 1.0
    elif primary == "SIDEWAYS":
        multiplier *= 0.7
    else:
        multiplier *= 0.4

    if vol == "HIGH_VOLATILITY":
        multiplier *= 0.5
    elif vol == "LOW_VOLATILITY":
        multiplier *= 1.0
    else:
        multiplier *= 0.85

    if risk_mode == "RISK_OFF":
        multiplier *= 0.8

    return round(max(0.0, min(1.0, multiplier)), 4)
