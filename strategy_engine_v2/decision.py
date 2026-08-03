from __future__ import annotations


def classify_decision(
    composite_score: float,
    confidence: float,
    *,
    buy_threshold: float = 35.0,
    sell_threshold: float = -35.0,
    watch_confidence: float = 45.0,
) -> str:
    if composite_score >= buy_threshold and confidence >= watch_confidence:
        return "BUY"
    if composite_score <= sell_threshold and confidence >= watch_confidence:
        return "SELL"
    if abs(composite_score) >= 15.0:
        return "WATCH"
    return "HOLD"
