from __future__ import annotations

from typing import Any


def signal_contributions(strategy_result: dict[str, Any]) -> list[dict[str, Any]]:
    decision = strategy_result.get("decision", {})
    reasons = decision.get("reasons", [])
    if not isinstance(reasons, list):
        reasons = []

    bullish = int(decision.get("bullish_count", 0))
    bearish = int(decision.get("bearish_count", 0))
    neutral = int(decision.get("neutral_count", 0))
    total = max(1, bullish + bearish + neutral)

    rows = []
    for index, reason in enumerate(reasons, start=1):
        rows.append({
            "rank": index,
            "reason": str(reason),
            "estimated_contribution_pct": round(100.0 / max(1, len(reasons)), 2),
        })

    return rows


def portfolio_contributions(portfolio_result: dict[str, Any]) -> list[dict[str, Any]]:
    portfolio = portfolio_result.get("portfolio", {})
    rows = portfolio.get("recommended_allocations", [])
    if not isinstance(rows, list):
        return []

    total = sum(float(row.get("recommended_weight_pct", 0)) for row in rows)
    output = []
    for row in rows:
        weight = float(row.get("recommended_weight_pct", 0))
        output.append({
            "symbol": row.get("symbol", "UNKNOWN"),
            "sector": row.get("sector", "UNKNOWN"),
            "rank": row.get("rank"),
            "recommended_weight_pct": round(weight, 4),
            "portfolio_contribution_pct": (
                round(weight / total * 100.0, 2) if total > 0 else 0.0
            ),
            "risk_adjusted_score": row.get("risk_adjusted_score", 0),
            "decision": row.get("decision", "HOLD"),
        })
    return output
