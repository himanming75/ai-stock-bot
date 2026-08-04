from __future__ import annotations


WEIGHTS = {
    "trend": 0.30,
    "price_extension": 0.10,
    "rsi_centered": 0.15,
    "volume_strength": 0.10,
    "market_trend": 0.20,
    "news_score": 0.15,
}


def calculate(features: dict[str, float]) -> float:
    raw = sum(features[name] * weight for name, weight in WEIGHTS.items())
    raw -= features["volatility_penalty"] * 0.15
    return round(max(-1.0, min(1.0, raw)), 6)
