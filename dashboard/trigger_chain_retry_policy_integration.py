import json
from pathlib import Path


def build_trigger_chain_retry_policy_payload(root: Path):
    path = (
        root / "release/v83_37_to_v83_40/actual/"
        "trigger_chain_retry_policy_dashboard_state.json"
    )
    if not path.exists():
        return {"trigger_retry_policy_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"trigger_retry_policy_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "trigger_retry_policy_state": "NOT_AVAILABLE"
    }
