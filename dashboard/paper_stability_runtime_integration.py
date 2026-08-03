import json
from pathlib import Path


def build_paper_stability_runtime_payload(root: Path):
    path = (
        root / "release/v83_81_to_v83_88/actual/"
        "paper_stability_runtime_dashboard_state.json"
    )
    if not path.exists():
        return {"paper_stability_runtime_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paper_stability_runtime_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "paper_stability_runtime_state": "NOT_AVAILABLE"
    }
