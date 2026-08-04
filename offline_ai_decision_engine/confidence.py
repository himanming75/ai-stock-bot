from __future__ import annotations


def calculate(score: float, regime: str, features: dict[str, float]) -> float:
    base = abs(score) * 100.0
    agreement = 0
    direction = 1 if score > 0 else -1 if score < 0 else 0
    for name in ("trend", "rsi_centered", "market_trend", "news_score"):
        value = features[name]
        if direction and value * direction > 0:
            agreement += 1
    confidence = base * 0.65 + (agreement / 4.0) * 25.0
    if regime == "HIGH_VOLATILITY":
        confidence -= 15.0
    return round(max(0.0, min(99.0, confidence)), 2)
