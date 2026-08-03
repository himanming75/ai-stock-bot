from __future__ import annotations

from typing import Iterable

from strategy_engine_v2.models import SignalInput


def aggregate_signals(signals: Iterable[SignalInput]) -> dict:
    enabled = [signal for signal in signals if signal.enabled]
    total_weight = sum(signal.normalized_weight() for signal in enabled)

    if not enabled or total_weight <= 0:
        return {
            "composite_score": 0.0,
            "confidence": 0.0,
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "signal_count": 0,
            "agreement_ratio": 0.0,
        }

    weighted_sum = sum(
        signal.normalized_score() * signal.normalized_weight()
        for signal in enabled
    )
    composite = weighted_sum / total_weight

    bullish = sum(1 for signal in enabled if signal.normalized_score() >= 20)
    bearish = sum(1 for signal in enabled if signal.normalized_score() <= -20)
    neutral = len(enabled) - bullish - bearish
    dominant = max(bullish, bearish, neutral)
    agreement_ratio = dominant / len(enabled)

    magnitude = min(1.0, abs(composite) / 100.0)
    confidence = ((agreement_ratio * 0.6) + (magnitude * 0.4)) * 100.0

    return {
        "composite_score": round(composite, 4),
        "confidence": round(confidence, 2),
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "signal_count": len(enabled),
        "agreement_ratio": round(agreement_ratio, 4),
    }
