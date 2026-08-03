from __future__ import annotations

from portfolio_scoring.models import Candidate


DECISION_MULTIPLIER = {
    "BUY": 1.00,
    "WATCH": 0.45,
    "HOLD": 0.10,
    "SELL": -1.00,
}


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def score_candidate(candidate: Candidate) -> dict:
    decision_multiplier = DECISION_MULTIPLIER.get(candidate.decision, 0.0)
    confidence_factor = clamp(candidate.confidence, 0.0, 100.0) / 100.0
    signal_factor = clamp(candidate.composite_score, -100.0, 100.0) / 100.0
    liquidity_factor = clamp(candidate.liquidity_score, 0.0, 100.0) / 100.0

    volatility_penalty = clamp(candidate.volatility_pct / 10.0, 0.0, 0.75)
    risk_factor = 1.0 - volatility_penalty

    raw_score = (
        (signal_factor * 55.0)
        + (confidence_factor * 30.0)
        + (liquidity_factor * 15.0)
    ) * decision_multiplier

    risk_adjusted_score = raw_score * risk_factor
    return {
        "symbol": candidate.symbol,
        "sector": candidate.sector,
        "decision": candidate.decision,
        "confidence": round(candidate.confidence, 4),
        "composite_score": round(candidate.composite_score, 4),
        "volatility_pct": round(candidate.volatility_pct, 4),
        "liquidity_score": round(candidate.liquidity_score, 4),
        "max_position_pct": round(
            clamp(candidate.max_position_pct, 0.0, 100.0), 4
        ),
        "risk_factor": round(risk_factor, 4),
        "raw_score": round(raw_score, 4),
        "risk_adjusted_score": round(risk_adjusted_score, 4),
    }


def rank_candidates(candidates: list[Candidate]) -> list[dict]:
    rows = [
        score_candidate(candidate)
        for candidate in candidates
        if candidate.enabled
    ]
    rows.sort(
        key=lambda row: (
            row["risk_adjusted_score"],
            row["confidence"],
            row["symbol"],
        ),
        reverse=True,
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows
