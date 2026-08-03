
import json
from pathlib import Path

def build_scheduled_runner_payload(root: Path):
    path = (
        root / "release/v83_17_to_v83_20/actual/"
        "scheduled_supervised_runner_dashboard_state.json"
    )
    if not path.exists():
        return {"scheduled_runner_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scheduled_runner_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "scheduled_runner_state": "NOT_AVAILABLE"
    }
