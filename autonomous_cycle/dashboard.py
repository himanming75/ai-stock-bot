from __future__ import annotations
from pathlib import Path
from autonomous_cycle.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v103_01_to_v103_32/actual/"
        "autonomous_cycle_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "cycle_id": result.get("cycle_id"),
        "cycle_date": result.get("cycle_date"),
        "cycle_action": result.get("cycle_action"),
        "steps": result.get("steps", []),
        "completed_step_count": result.get("completed_step_count", 0),
        "failed_steps": result.get("failed_steps", []),
        "duplicate": result.get("duplicate", {}),
        "checkpoint": result.get("checkpoint", {}),
        "approval_granted": False,
        "execution_authorized": False,
        "paper_only": True,
    }
