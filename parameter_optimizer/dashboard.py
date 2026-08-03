from __future__ import annotations
from pathlib import Path
from parameter_optimizer.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v91_33_to_v91_64/actual/"
        "parameter_optimization_result.json"
    )
    stable = result.get("best_stable_candidate")
    candidate = result.get("best_candidate")
    return {
        "parameter_optimization_state": result.get(
            "state", "NOT_AVAILABLE"
        ),
        "evaluated_combination_count": result.get(
            "evaluated_combination_count", 0
        ),
        "stable_combination_count": result.get(
            "stable_combination_count", 0
        ),
        "best_stable_strategy": (
            stable.get("strategy_id") if stable else None
        ),
        "best_stable_parameters": (
            stable.get("parameters") if stable else None
        ),
        "best_candidate_strategy": (
            candidate.get("strategy_id") if candidate else None
        ),
        "best_candidate_parameters": (
            candidate.get("parameters") if candidate else None
        ),
        "top_results": result.get("top_results", [])[:10],
        "paper_only": True,
    }
