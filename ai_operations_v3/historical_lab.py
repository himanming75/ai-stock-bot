from __future__ import annotations
from decimal import Decimal
from typing import Any


class HistoricalAILab:
    def summarize(
        self,
        *,
        ai_v2_final: dict[str, Any],
    ) -> dict[str, Any]:
        optimization = ai_v2_final.get("parameter_optimization", {})
        walk_forward = ai_v2_final.get("walk_forward_validation", {})
        monte_carlo = ai_v2_final.get("monte_carlo_simulation", {})
        champion = ai_v2_final.get("champion_challenger", {})

        grid = optimization.get("grid_search", {})
        random_search = optimization.get("random_search", {})
        rows = []
        for method, result in (
            ("GRID_SEARCH", grid),
            ("RANDOM_SEARCH", random_search),
        ):
            best = result.get("best", {})
            if best:
                rows.append({
                    "method": method,
                    "parameters": best.get("parameters", {}),
                    "score": best.get("score", "0"),
                    "evaluation_count": result.get("evaluation_count", 0),
                })

        return {
            "optimization_leaders": rows,
            "walk_forward_window_count": walk_forward.get("window_count", 0),
            "walk_forward_positive_ratio": walk_forward.get(
                "positive_window_ratio", "0"
            ),
            "monte_carlo_simulations": monte_carlo.get(
                "simulation_count", 0
            ),
            "monte_carlo_risk_of_ruin": monte_carlo.get(
                "risk_of_ruin", "0"
            ),
            "champion_candidate": champion.get(
                "champion_candidate", {}
            ),
            "promotion_eligible": champion.get(
                "promotion_eligible", False
            ),
            "actual_research_execution_requested": False,
            "actual_strategy_promotion_performed": False,
        }
