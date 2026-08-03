from __future__ import annotations
from v89_portfolio.scoring import rank_strategies
from v89_portfolio.sizing import (
    equal_weight,
    score_weight,
    inverse_drawdown_weight,
    capped_weights,
    kelly_fraction,
)
from v89_portfolio.risk import evaluate_portfolio_risk

def optimize(source: dict, policy: dict) -> dict:
    rankings = source.get("strategy_rankings", [])
    ranked = rank_strategies(rankings)
    eligible = [
        row for row in ranked
        if row.get("gate", {}).get("approved") is True
    ]
    if not eligible:
        eligible = ranked[: max(1, int(policy.get("fallback_top_n", 3)))]

    mode = str(policy.get("allocation_mode", "SCORE_WEIGHT")).upper()
    if mode == "EQUAL_WEIGHT":
        weights = equal_weight([row["strategy"] for row in eligible])
    elif mode == "INVERSE_DRAWDOWN":
        weights = inverse_drawdown_weight(eligible)
    else:
        weights = score_weight(eligible)

    cap = float(policy.get("maximum_single_allocation_pct", 40.0)) / 100.0
    weights = capped_weights(weights, cap)

    allocations = []
    for row in eligible:
        name = row["strategy"]
        allocations.append({
            "strategy": name,
            "weight_pct": round(weights.get(name, 0.0) * 100.0, 4),
            "kelly_fraction": round(
                kelly_fraction(
                    float(row.get("win_rate_pct", 0.0)),
                    float(row.get("profit_factor", 0.0)),
                ),
                4,
            ),
            "score": row["portfolio_score"],
            "rank": row["portfolio_rank"],
            "approved": row.get("gate", {}).get("approved", False),
        })

    risk = evaluate_portfolio_risk(weights, ranked, policy)
    state = (
        "PORTFOLIO_OPTIMIZATION_APPROVED"
        if risk["passed"]
        else "PORTFOLIO_OPTIMIZATION_REVIEW_REQUIRED"
    )
    return {
        "state": state,
        "ranked_strategies": ranked,
        "eligible_strategy_count": len(eligible),
        "allocation_mode": mode,
        "allocations": allocations,
        "risk": risk,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
