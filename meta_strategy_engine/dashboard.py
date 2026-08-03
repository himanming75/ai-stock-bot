from __future__ import annotations
from pathlib import Path
from meta_strategy_engine.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v94_01_to_v94_32/actual/meta_strategy_result.json"
    )
    return {
        "meta_strategy_state": result.get("state", "NOT_AVAILABLE"),
        "paper_decision": result.get("paper_decision"),
        "selected_strategy": result.get("selected_strategy"),
        "strategy_allocations": result.get("strategy_allocations", []),
        "final_position_multiplier": result.get("final_position_multiplier", 0.0),
        "failed_checks": result.get("failed_checks", []),
        "paper_only": True,
    }
