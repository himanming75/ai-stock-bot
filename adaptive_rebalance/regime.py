from __future__ import annotations
from typing import Any

def normalize_regime(source: dict[str, Any]) -> dict[str, Any]:
    regime = str(
        source.get("primary_regime", source.get("regime", "UNKNOWN"))
    ).upper()
    volatility = str(
        source.get(
            "volatility_regime",
            source.get("volatility", "NORMAL_VOLATILITY"),
        )
    ).upper()
    confidence = float(source.get("confidence_score", 50.0))
    return {
        "primary_regime": regime,
        "volatility_regime": volatility,
        "confidence_score": round(confidence, 6),
    }

def regime_multiplier(regime: dict[str, Any], policy: dict[str, Any]) -> float:
    mapping = policy.get("regime_multipliers", {})
    primary = regime.get("primary_regime", "UNKNOWN")
    volatility = regime.get("volatility_regime", "NORMAL_VOLATILITY")
    primary_multiplier = float(mapping.get(primary, 1.0))
    volatility_multiplier = float(mapping.get(volatility, 1.0))
    confidence = max(0.0, min(1.0, float(regime.get("confidence_score", 50.0)) / 100.0))
    blended = 1.0 + (primary_multiplier * volatility_multiplier - 1.0) * confidence
    return round(blended, 6)
