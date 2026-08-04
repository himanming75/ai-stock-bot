from __future__ import annotations
from typing import Any

PROFILE_BONUS = {"SCALP": 2.0, "DAY": 4.0, "SWING": 3.0}

def score(signal: dict[str, Any]) -> dict[str, Any]:
    confidence = float(signal.get("confidence", 0) or 0)
    trend = float(signal.get("trend_alignment", 0) or 0)
    volume = float(signal.get("volume_confirmation", 0) or 0)
    volatility_penalty = float(signal.get("volatility_penalty", 0) or 0)
    spread_penalty = float(signal.get("spread_penalty", 0) or 0)
    raw = (
        confidence * 0.50
        + trend * 0.20
        + volume * 0.20
        + PROFILE_BONUS.get(str(signal.get("profile")), 0)
        - volatility_penalty * 0.05
        - spread_penalty * 0.05
    )
    return {**signal, "strategy_score": round(max(0.0, min(100.0, raw)), 4)}
