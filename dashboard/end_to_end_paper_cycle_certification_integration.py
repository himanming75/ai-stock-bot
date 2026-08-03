import json
from pathlib import Path


def build_end_to_end_paper_cycle_certification_payload(root: Path):
    path = (
        root / "release/v83_65_to_v83_68/actual/"
        "end_to_end_paper_cycle_certification_dashboard_state.json"
    )
    if not path.exists():
        return {"paper_cycle_certification_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paper_cycle_certification_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "paper_cycle_certification_state": "NOT_AVAILABLE"
    }
