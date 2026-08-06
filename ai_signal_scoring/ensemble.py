from __future__ import annotations
from .components import (
    direction_score,
    momentum_score,
    regime_score,
    risk_score,
    trend_score,
    volatility_score,
    volume_score,
)


DEFAULT_WEIGHTS = {
    "direction": 0.15,
    "trend": 0.20,
    "momentum": 0.18,
    "volume": 0.10,
    "volatility": 0.12,
    "regime": 0.15,
    "risk": 0.10,
}


def score_candidate(candidate: dict, weights: dict | None = None) -> dict:
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    total_weight = sum(float(v) for v in weights.values())
    if total_weight <= 0:
        raise ValueError("ENSEMBLE_WEIGHT_REQUIRED")
    normalized = {
        key: float(value) / total_weight
        for key, value in weights.items()
    }

    features = candidate.get("features", {})
    components = {
        "direction": direction_score(candidate),
        "trend": trend_score(features),
        "momentum": momentum_score(features),
        "volume": volume_score(features),
        "volatility": volatility_score(features),
        "regime": regime_score(candidate),
        "risk": risk_score(candidate),
    }

    weighted = sum(
        components[name] * normalized.get(name, 0.0)
        for name in components
    )

    conflict_count = int(
        candidate.get("conflict_analysis", {}).get("conflict_count") or 0
    )
    conflict_penalty = min(30.0, conflict_count * 10.0)
    final_score = max(0.0, min(100.0, weighted - conflict_penalty))

    base_confidence = float(candidate.get("confidence") or 0)
    confidence = min(
        100.0,
        max(
            0.0,
            final_score * 0.65 + base_confidence * 0.35 - conflict_penalty,
        ),
    )

    return {
        "component_scores": {
            key: round(value, 2)
            for key, value in components.items()
        },
        "weights": {
            key: round(value, 4)
            for key, value in normalized.items()
        },
        "conflict_penalty": round(conflict_penalty, 2),
        "ai_score": round(final_score, 2),
        "ensemble_confidence": round(confidence, 2),
    }
