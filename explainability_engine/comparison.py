from __future__ import annotations

from typing import Any


def compare_ranked_candidates(
    portfolio_result: dict[str, Any],
) -> list[dict[str, Any]]:
    portfolio = portfolio_result.get("portfolio", {})
    rows = portfolio.get("ranked_candidates", [])
    if not isinstance(rows, list):
        return []

    comparisons = []
    for current, following in zip(rows, rows[1:]):
        gap = (
            float(current.get("risk_adjusted_score", 0))
            - float(following.get("risk_adjusted_score", 0))
        )
        comparisons.append({
            "higher_rank_symbol": current.get("symbol"),
            "lower_rank_symbol": following.get("symbol"),
            "score_gap": round(gap, 4),
            "explanation": (
                f"{current.get('symbol')} ranks above {following.get('symbol')} "
                f"by {gap:.2f} risk-adjusted points. "
                f"Confidence is {float(current.get('confidence', 0)):.2f}% versus "
                f"{float(following.get('confidence', 0)):.2f}%."
            ),
        })
    return comparisons
