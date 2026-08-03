import json
from pathlib import Path


def build_retry_cycle_completion_payload(root: Path):
    path = (
        root / "release/v83_53_to_v83_56/actual/"
        "retry_cycle_completion_dashboard_state.json"
    )
    if not path.exists():
        return {"retry_cycle_completion_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"retry_cycle_completion_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "retry_cycle_completion_state": "NOT_AVAILABLE"
    }
