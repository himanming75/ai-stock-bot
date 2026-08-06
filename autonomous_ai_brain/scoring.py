from __future__ import annotations
from decimal import Decimal
from .models import StrategyCandidate, StrategyScore


D = Decimal


def score_candidate(candidate: StrategyCandidate) -> Decimal:
    reward = (
        candidate.confidence * D("0.25")
        + candidate.expected_return * D("0.20")
        + candidate.regime_fit * D("0.25")
        + candidate.stability * D("0.20")
    )
    risk_penalty = (
        candidate.drawdown_risk * D("0.30")
    )
    evidence_bonus = min(
        D(str(candidate.evidence_count)) / D("100"),
        D("1"),
    ) * D("0.10")
    return reward - risk_penalty + evidence_bonus


def rank_candidates(
    candidates: list[StrategyCandidate],
    *,
    minimum_evidence: int = 20,
    maximum_drawdown_risk: Decimal = D("0.55"),
    minimum_stability: Decimal = D("0.45"),
) -> list[StrategyScore]:
    raw = []
    for candidate in candidates:
        reasons = []
        if candidate.evidence_count < minimum_evidence:
            reasons.append("INSUFFICIENT_EVIDENCE")
        if candidate.drawdown_risk > maximum_drawdown_risk:
            reasons.append("DRAWDOWN_RISK_TOO_HIGH")
        if candidate.stability < minimum_stability:
            reasons.append("STABILITY_TOO_LOW")
        raw.append({
            "strategy_id": candidate.strategy_id,
            "score": score_candidate(candidate),
            "eligible": not reasons,
            "reasons": tuple(reasons),
        })

    raw.sort(
        key=lambda item: (
            not item["eligible"],
            -item["score"],
            item["strategy_id"],
        )
    )
    return [
        StrategyScore(
            strategy_id=item["strategy_id"],
            total_score=item["score"],
            rank=index + 1,
            eligible=item["eligible"],
            rejection_reasons=item["reasons"],
        )
        for index, item in enumerate(raw)
    ]
