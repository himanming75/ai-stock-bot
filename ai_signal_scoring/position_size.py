from __future__ import annotations


def recommend_position_size(
    *,
    ai_score: float,
    confidence: float,
    risk_component: float,
    max_position_percent: float = 10.0,
) -> dict:
    quality = max(
        0.0,
        min(
            1.0,
            (float(ai_score) / 100)
            * (float(confidence) / 100)
            * (float(risk_component) / 100),
        ),
    )
    suggested = round(max_position_percent * quality, 2)
    return {
        "suggested_position_percent": suggested,
        "maximum_position_percent": float(max_position_percent),
        "mode": "CANDIDATE_ONLY",
        "position_order_enabled": False,
        "capital_allocation_enabled": False,
    }
