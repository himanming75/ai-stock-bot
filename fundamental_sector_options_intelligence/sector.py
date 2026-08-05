from __future__ import annotations
from .utils import clamp, f


def score_sector(item: dict) -> dict:
    return_1m = f(item.get("return_1m"))
    return_3m = f(item.get("return_3m"))
    return_6m = f(item.get("return_6m"))
    relative_strength = f(item.get("relative_strength"))
    breadth = f(item.get("breadth"))
    earnings_revision = f(item.get("earnings_revision"))
    fund_flow = f(item.get("fund_flow"))
    volatility = f(item.get("volatility"))

    momentum = clamp(
        return_1m * 2.5
        + return_3m * 1.6
        + return_6m * 0.8
    )
    participation = clamp(
        breadth * 0.65
        + relative_strength * 0.75
    )
    support = clamp(
        earnings_revision * 0.7
        + fund_flow * 0.5
    )
    volatility_penalty = min(max(volatility - 0.20, 0.0) * 1.2, 0.5)

    score = clamp(
        momentum * 0.40
        + participation * 0.32
        + support * 0.28
        - volatility_penalty
    )

    return {
        "sector": str(item.get("sector", "UNKNOWN")),
        "sector_score": round(score, 8),
        "momentum_score": round(momentum, 8),
        "participation_score": round(participation, 8),
        "support_score": round(support, 8),
        "volatility_penalty": round(volatility_penalty, 8),
    }
