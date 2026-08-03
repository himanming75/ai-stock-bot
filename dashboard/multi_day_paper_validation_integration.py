import json
from pathlib import Path


def build_multi_day_paper_validation_payload(root: Path):
    path = (
        root / "release/v83_77_to_v83_80/actual/"
        "multi_day_paper_validation_dashboard_state.json"
    )
    if not path.exists():
        return {"multi_day_paper_validation_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"multi_day_paper_validation_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "multi_day_paper_validation_state": "NOT_AVAILABLE"
    }
