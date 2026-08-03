import json
from pathlib import Path


def build_local_trigger_dispatcher_payload(root: Path):
    path = (
        root / "release/v83_29_to_v83_32/actual/"
        "local_trigger_dispatcher_dashboard_state.json"
    )
    if not path.exists():
        return {"local_trigger_dispatch_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"local_trigger_dispatch_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "local_trigger_dispatch_state": "NOT_AVAILABLE"
    }
