import json
from pathlib import Path

def build_supervised_reentry_runner_payload(root: Path):
    path = (
        root / "release/v83_49_to_v83_52/actual/"
        "supervised_reentry_runner_dashboard_state.json"
    )
    if not path.exists():
        return {"supervised_reentry_runner_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"supervised_reentry_runner_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "supervised_reentry_runner_state": "NOT_AVAILABLE"
    }
