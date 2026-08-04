from __future__ import annotations


RANK_BONUS = {"A": 12.0, "B": 7.0, "C": 2.0, "D": -8.0}


def selection_score(signal: dict, liquidity_score: float) -> float:
    confidence = float(signal["confidence"])
    risk = float(signal["risk_score"])
    raw = (
        confidence * 0.55
        + (100.0 - risk) * 0.25
        + max(0.0, min(100.0, liquidity_score)) * 0.10
        + RANK_BONUS.get(str(signal["signal_rank"]), -10.0)
        + max(-10.0, min(10.0, float(signal["signal_score"]) * 10.0))
    )
    if signal["action"] != "BUY":
        raw -= 25.0
    return round(max(0.0, min(100.0, raw)), 4)


def portfolio_score(selected: list[dict]) -> float:
    if not selected:
        return 0.0
    return round(sum(float(item["selection_score"]) for item in selected) / len(selected), 4)
