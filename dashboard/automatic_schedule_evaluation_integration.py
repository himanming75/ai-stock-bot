
import json
from pathlib import Path

def build_automatic_schedule_payload(root: Path):
    path = (
        root / "release/v83_25_to_v83_28/actual/"
        "automatic_schedule_dashboard_state.json"
    )
    if not path.exists():
        return {"automatic_schedule_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"automatic_schedule_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "automatic_schedule_state": "NOT_AVAILABLE"
    }
