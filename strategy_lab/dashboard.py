from __future__ import annotations
from pathlib import Path
from strategy_lab.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(root / "release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json")
    return {
        "strategy_lab_state": result.get("state", "NOT_AVAILABLE"),
        "registered_strategy_count": result.get("registered_strategy_count", 0),
        "executed_strategy_count": result.get("executed_strategy_count", 0),
        "approved_strategy_count": result.get("approved_strategy_count", 0),
        "champion": (
            result.get("champion", {}).get("strategy_name")
            if result.get("champion") else None
        ),
        "top_candidate": (
            result.get("top_candidate", {}).get("strategy_name")
            if result.get("top_candidate") else None
        ),
        "top_10": result.get("rankings", [])[:10],
        "paper_only": True,
    }
