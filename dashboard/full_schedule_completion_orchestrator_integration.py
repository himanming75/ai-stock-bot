import json
from pathlib import Path


def build_full_schedule_completion_orchestrator_payload(root: Path):
    path = (
        root / "release/v83_57_to_v83_60/actual/"
        "full_schedule_completion_orchestrator_dashboard_state.json"
    )
    if not path.exists():
        return {"full_cycle_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"full_cycle_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "full_cycle_state": "NOT_AVAILABLE"
    }
