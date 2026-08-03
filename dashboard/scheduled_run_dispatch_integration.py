
import json
from pathlib import Path

def build_scheduled_dispatch_payload(root: Path):
    path = (
        root / "release/v83_21_to_v83_24/actual/"
        "scheduled_run_dispatch_dashboard_state.json"
    )
    if not path.exists():
        return {"scheduled_dispatch_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scheduled_dispatch_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "scheduled_dispatch_state": "NOT_AVAILABLE"
    }
