from __future__ import annotations
from decimal import Decimal

from .models import StrategyPerformance


D = Decimal


def performance_score(
    item: StrategyPerformance,
) -> Decimal:
    evidence = min(
        D(str(item.trade_count)) / D("300"),
        D("1"),
    )
    return (
        item.win_rate * D("0.20")
        + item.expected_return * D("0.20")
        + item.sharpe_ratio * D("0.20")
        + item.stability * D("0.20")
        + evidence * D("0.10")
        - item.max_drawdown * D("0.30")
    )


def compare_champion_challenger(
    champion: StrategyPerformance,
    challenger: StrategyPerformance,
    *,
    minimum_trade_count: int = 100,
    minimum_improvement: Decimal = D("0.05"),
) -> dict:
    champion_score = performance_score(champion)
    challenger_score = performance_score(challenger)
    improvement = challenger_score - champion_score

    reasons = []
    eligible = True

    if challenger.trade_count < minimum_trade_count:
        eligible = False
        reasons.append("INSUFFICIENT_CHALLENGER_EVIDENCE")

    if challenger.max_drawdown > champion.max_drawdown * D("1.20"):
        eligible = False
        reasons.append("CHALLENGER_DRAWDOWN_TOO_HIGH")

    if challenger.stability < D("0.55"):
        eligible = False
        reasons.append("CHALLENGER_STABILITY_TOO_LOW")

    recommended = (
        eligible
        and improvement >= minimum_improvement
    )

    return {
        "champion": champion.to_dict(),
        "challenger": challenger.to_dict(),
        "champion_score": str(champion_score),
        "challenger_score": str(challenger_score),
        "improvement": str(improvement),
        "eligible": eligible,
        "promotion_recommended": recommended,
        "automatic_promotion_performed": False,
        "reasons": reasons,
    }
