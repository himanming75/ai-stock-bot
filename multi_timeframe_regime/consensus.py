from __future__ import annotations
from collections import Counter
from typing import Any

REGIME_SCORE = {"BULL": 1.0, "SIDEWAYS": 0.0, "BEAR": -1.0}
VOL_SCORE = {"LOW_VOLATILITY": 1.0, "NORMAL_VOLATILITY": 0.5, "HIGH_VOLATILITY": 0.0}

def build_consensus(
    frames: list[dict[str, Any]],
    weights: dict[str, float],
) -> dict[str, Any]:
    total_weight = 0.0
    weighted_regime = 0.0
    weighted_volatility = 0.0
    risk_off_weight = 0.0
    primary_values = []

    for frame in frames:
        name = frame["frame_name"]
        weight = float(weights.get(name, 1.0))
        regime = frame["regime"]
        total_weight += weight
        weighted_regime += REGIME_SCORE.get(regime["primary_regime"], 0.0) * weight
        weighted_volatility += VOL_SCORE.get(regime["volatility_regime"], 0.5) * weight
        if regime["risk_mode"] == "RISK_OFF":
            risk_off_weight += weight
        primary_values.append(regime["primary_regime"])

    if total_weight <= 0:
        total_weight = 1.0

    normalized_regime = weighted_regime / total_weight
    normalized_volatility = weighted_volatility / total_weight
    alignment = max(Counter(primary_values).values(), default=0) / len(primary_values) * 100.0 if primary_values else 0.0

    if normalized_regime >= 0.35:
        primary = "BULL"
    elif normalized_regime <= -0.35:
        primary = "BEAR"
    else:
        primary = "SIDEWAYS"

    if normalized_volatility <= 0.25:
        volatility = "HIGH_VOLATILITY"
    elif normalized_volatility >= 0.75:
        volatility = "LOW_VOLATILITY"
    else:
        volatility = "NORMAL_VOLATILITY"

    risk_mode = "RISK_OFF" if risk_off_weight / total_weight >= 0.5 else "RISK_ON"
    conflict = alignment < 67.0

    return {
        "primary_regime": primary,
        "volatility_regime": volatility,
        "risk_mode": risk_mode,
        "alignment_pct": round(alignment, 2),
        "conflict_detected": conflict,
        "weighted_regime_score": round(normalized_regime, 4),
        "weighted_volatility_score": round(normalized_volatility, 4),
    }
