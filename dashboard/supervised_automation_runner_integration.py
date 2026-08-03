
import json
from pathlib import Path

def build_supervised_runner_payload(root: Path):
    path = root / "release/v83_13_to_v83_16/actual/supervised_automation_runner_dashboard_state.json"
    if not path.exists():
        return {"supervised_runner_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"supervised_runner_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {"supervised_runner_state": "NOT_AVAILABLE"}
