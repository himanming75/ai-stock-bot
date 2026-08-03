from __future__ import annotations
from pathlib import Path
from paper_execution_simulator.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json"
    )
    return {
        "paper_simulation_state": result.get("state", "NOT_AVAILABLE"),
        "simulation_date": result.get("simulation_date"),
        "cycle_id": result.get("cycle_id"),
        "duplicate_cycle": result.get("duplicate_cycle", False),
        "fill_summary": result.get("fill_summary", {}),
        "portfolio": result.get("portfolio", {}),
        "actual_orders_submitted": 0,
        "paper_only": True,
    }
