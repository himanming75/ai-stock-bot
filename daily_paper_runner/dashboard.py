from __future__ import annotations
from pathlib import Path
from daily_paper_runner.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v106_01_to_v106_32/actual/"
        "daily_paper_runner_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "run_id": result.get("run_id"),
        "selected_session": result.get("selected_session", {}),
        "preflight": result.get("preflight", {}),
        "paper_approval": result.get("paper_approval", {}),
        "daily_plan": result.get("daily_plan", {}),
        "daily_report": result.get("daily_report", {}),
        "paper_simulation_authorized": result.get(
            "paper_simulation_authorized"
        ),
        "live_execution_authorized": False,
        "actual_orders_submitted": 0,
        "paper_only": True,
    }
