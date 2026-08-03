from __future__ import annotations

from typing import Any

from portfolio_scoring.allocation import allocate
from portfolio_scoring.diversification import diversification_score
from portfolio_scoring.models import Candidate
from portfolio_scoring.scoring import rank_candidates


def evaluate_portfolio(
    candidates: list[Candidate],
    policy: dict[str, Any],
) -> dict[str, Any]:
    ranked = rank_candidates(candidates)

    allocations, allocation_summary = allocate(
        ranked,
        portfolio_exposure_pct=float(
            policy.get("maximum_portfolio_exposure_pct", 50.0)
        ),
        sector_limit_pct=float(
            policy.get("maximum_sector_exposure_pct", 25.0)
        ),
        minimum_score=float(
            policy.get("minimum_risk_adjusted_score", 5.0)
        ),
    )

    div_score = diversification_score(
        allocations,
        allocation_summary["sector_allocations_pct"],
    )

    return {
        "candidate_count": len(candidates),
        "ranked_count": len(ranked),
        "ranked_candidates": ranked,
        "recommended_allocations": allocations,
        "allocation_summary": allocation_summary,
        "diversification_score": div_score,
        "portfolio_score": round(
            (
                (
                    sum(
                        max(0.0, row["risk_adjusted_score"])
                        for row in allocations
                    )
                    / max(1, len(allocations))
                )
                * 0.7
            )
            + (div_score * 0.3),
            2,
        ),
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
