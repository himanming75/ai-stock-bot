from __future__ import annotations
from typing import Any

def extract_candidate(result: dict[str, Any]) -> dict[str, Any]:
    return (
        result.get("best_stable_candidate")
        or result.get("best_candidate")
        or {}
    )

def derive_features(candidate: dict[str, Any]) -> dict[str, Any]:
    full = candidate.get("full_result", {})
    walk = candidate.get("walk_forward", {})
    gate = candidate.get("stability_gate", {})
    return {
        "strategy_id": candidate.get("strategy_id"),
        "base_strategy": candidate.get("base_strategy"),
        "parameters": candidate.get("parameters", {}),
        "optimization_score": candidate.get("optimization_score", 0.0),
        "total_return_pct": full.get("total_return_pct", 0.0),
        "maximum_drawdown_pct": full.get("maximum_drawdown_pct", 0.0),
        "sharpe_ratio": full.get("sharpe_ratio", 0.0),
        "profit_factor": full.get("profit_factor", 0.0),
        "win_rate_pct": full.get("win_rate_pct", 0.0),
        "total_trades": full.get("total_trades", 0),
        "positive_window_pct": walk.get("positive_window_pct", 0.0),
        "average_window_return_pct": walk.get("average_return_pct", 0.0),
        "worst_window_return_pct": walk.get("worst_return_pct", 0.0),
        "best_window_return_pct": walk.get("best_return_pct", 0.0),
        "worst_window_drawdown_pct": walk.get("worst_drawdown_pct", 0.0),
        "average_window_sharpe": walk.get("average_sharpe", 0.0),
        "stability_passed": gate.get("passed", False),
        "stability_failed_checks": gate.get("failed", []),
    }
