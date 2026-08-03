import json
from pathlib import Path


def build_crash_recovery_restart_payload(root: Path):
    path = (
        root / "release/v83_61_to_v83_64/actual/"
        "crash_recovery_restart_dashboard_state.json"
    )
    if not path.exists():
        return {"restart_recovery_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"restart_recovery_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "restart_recovery_state": "NOT_AVAILABLE"
    }
