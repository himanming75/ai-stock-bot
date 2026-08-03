import json
from pathlib import Path


def build_paper_autonomous_mode_payload(root: Path):
    path = (
        root / "release/v83_73_to_v83_76/actual/"
        "paper_autonomous_mode_dashboard_state.json"
    )
    if not path.exists():
        return {"paper_autonomous_mode_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paper_autonomous_mode_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "paper_autonomous_mode_state": "NOT_AVAILABLE"
    }
