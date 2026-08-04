from __future__ import annotations


WEIGHTS = {
    "trend": 0.27,
    "momentum": 0.18,
    "macd": 0.15,
    "volume": 0.10,
    "market_trend": 0.18,
    "news": 0.12,
}


def score(components: dict[str, float], pattern_bias: float) -> float:
    value = sum(components[name] * weight for name, weight in WEIGHTS.items())
    value += pattern_bias * 0.10
    value -= components["volatility"] * 0.12
    return round(max(-1.0, min(1.0, value)), 6)


def rank(confidence: float, absolute_score: float) -> str:
    if confidence >= 85 and absolute_score >= 0.60:
        return "A"
    if confidence >= 70 and absolute_score >= 0.40:
        return "B"
    if confidence >= 55 and absolute_score >= 0.20:
        return "C"
    return "D"
