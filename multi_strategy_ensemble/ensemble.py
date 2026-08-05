from __future__ import annotations
from .utils import clamp, signal

DEFAULT_WEIGHTS = {
    "MOMENTUM": 0.22,
    "TREND_FOLLOWING": 0.22,
    "MEAN_REVERSION": 0.14,
    "BREAKOUT": 0.16,
    "VWAP_MOMENTUM": 0.14,
    "VOLATILITY_EXPANSION": 0.12,
}

REGIME_MULTIPLIERS = {
    "BULL_TREND": {
        "MOMENTUM": 1.2, "TREND_FOLLOWING": 1.25, "BREAKOUT": 1.15,
        "MEAN_REVERSION": 0.7, "VWAP_MOMENTUM": 1.05, "VOLATILITY_EXPANSION": 1.0,
    },
    "BEAR_TREND": {
        "MOMENTUM": 1.15, "TREND_FOLLOWING": 1.25, "BREAKOUT": 1.05,
        "MEAN_REVERSION": 0.75, "VWAP_MOMENTUM": 1.0, "VOLATILITY_EXPANSION": 1.05,
    },
    "HIGH_VOLATILITY": {
        "MOMENTUM": 0.9, "TREND_FOLLOWING": 0.95, "BREAKOUT": 1.2,
        "MEAN_REVERSION": 0.65, "VWAP_MOMENTUM": 0.9, "VOLATILITY_EXPANSION": 1.35,
    },
    "SIDEWAYS_OR_MIXED": {
        "MOMENTUM": 0.8, "TREND_FOLLOWING": 0.8, "BREAKOUT": 0.75,
        "MEAN_REVERSION": 1.35, "VWAP_MOMENTUM": 1.0, "VOLATILITY_EXPANSION": 0.8,
    },
}

def combine(results: list[dict], regime: str) -> dict:
    multipliers = REGIME_MULTIPLIERS.get(regime, {})
    weighted_sum = 0.0
    weight_sum = 0.0
    bullish = bearish = neutral = 0
    for item in results:
        weight = DEFAULT_WEIGHTS[item["name"]] * multipliers.get(item["name"], 1.0)
        weighted_sum += item["score"] * weight
        weight_sum += weight
        bullish += item["signal"] == "BULLISH"
        bearish += item["signal"] == "BEARISH"
        neutral += item["signal"] == "NEUTRAL"

    score = clamp(weighted_sum / weight_sum if weight_sum else 0.0)
    disagreement = 1.0 - max(bullish, bearish, neutral) / max(len(results), 1)
    raw_confidence = 45.0 + abs(score) * 0.42 - disagreement * 35.0
    confidence = clamp(raw_confidence, 0.0, 100.0)
    final_signal = signal(score, 22.0)
    if disagreement >= 0.66:
        final_signal = "NEUTRAL"
        confidence = min(confidence, 45.0)
    return {
        "ensemble_score": round(score, 6),
        "ensemble_signal": final_signal,
        "confidence": round(confidence, 6),
        "disagreement": round(disagreement, 6),
        "bullish_votes": bullish,
        "bearish_votes": bearish,
        "neutral_votes": neutral,
        "strategy_count": len(results),
    }
