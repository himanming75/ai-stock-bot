import json
from pathlib import Path


def build_operator_control_center_payload(root: Path):
    path = (
        root / "release/v83_69_to_v83_72/actual/"
        "operator_control_center_unified_dashboard.json"
    )
    if not path.exists():
        return {"operator_control_center_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"operator_control_center_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "operator_control_center_state": "NOT_AVAILABLE"
    }
