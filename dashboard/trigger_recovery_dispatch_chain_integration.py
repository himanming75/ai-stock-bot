import json
from pathlib import Path


def build_trigger_recovery_dispatch_chain_payload(root: Path):
    path = (
        root / "release/v83_33_to_v83_36/actual/"
        "trigger_recovery_dispatch_chain_dashboard_state.json"
    )
    if not path.exists():
        return {"trigger_dispatch_chain_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"trigger_dispatch_chain_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "trigger_dispatch_chain_state": "NOT_AVAILABLE"
    }
