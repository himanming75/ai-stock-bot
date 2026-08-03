from __future__ import annotations

import json
from pathlib import Path


def build_paper_production_release_payload(root: Path) -> dict:
    path = (
        root / "release/v88_17_to_v88_24/actual/"
        "paper_production_release_dashboard_state.json"
    )
    if not path.exists():
        return {"paper_production_release_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"paper_production_release_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "paper_production_release_state": "NOT_AVAILABLE"
    }
