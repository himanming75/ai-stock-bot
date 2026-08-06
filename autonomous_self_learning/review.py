from __future__ import annotations
from decimal import Decimal


D = Decimal


def champion_review(
    summaries: list[dict],
    *,
    current_champion: str,
) -> dict:
    by_id = {
        item["strategy_id"]: item
        for item in summaries
    }

    current = by_id.get(current_champion)
    eligible = [
        item for item in summaries
        if item["status"] in {"HEALTHY", "WATCH"}
        and int(item["trade_count"]) >= 20
    ]

    if not eligible:
        return {
            "current_champion": current_champion,
            "recommended_champion": current_champion,
            "recommendation": "HOLD",
            "reason": "NO_ELIGIBLE_CHALLENGER",
            "automatic_change_performed": False,
        }

    def score(item: dict) -> Decimal:
        return (
            D(item["win_rate"]) * D("0.25")
            + D(item["profit_factor"]) * D("0.20")
            + D(item["sharpe_proxy"]) * D("0.20")
            + D(item["stability"]) * D("0.20")
            - D(item["max_drawdown"]) * D("0.30")
        )

    best = sorted(
        eligible,
        key=lambda item: (
            -score(item),
            item["strategy_id"],
        ),
    )[0]

    if current is None:
        recommendation = "REVIEW_CHANGE"
        reason = "CURRENT_CHAMPION_NOT_FOUND"
    elif best["strategy_id"] == current_champion:
        recommendation = "HOLD"
        reason = "CURRENT_CHAMPION_REMAINS_BEST"
    else:
        improvement = score(best) - score(current)
        if improvement >= D("0.05"):
            recommendation = "REVIEW_CHANGE"
            reason = "CHALLENGER_OUTPERFORMS_CHAMPION"
        else:
            recommendation = "HOLD"
            reason = "IMPROVEMENT_BELOW_THRESHOLD"

    return {
        "current_champion": current_champion,
        "recommended_champion": best["strategy_id"],
        "recommendation": recommendation,
        "reason": reason,
        "automatic_change_performed": False,
    }
