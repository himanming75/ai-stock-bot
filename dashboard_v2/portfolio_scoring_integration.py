from __future__ import annotations

import json
from pathlib import Path


def build_portfolio_scoring_payload(root: Path) -> dict:
    path = (
        root / "release/v86_17_to_v86_24/actual/"
        "portfolio_scoring_result.json"
    )
    if not path.exists():
        return {"portfolio_scoring_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"portfolio_scoring_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "portfolio_scoring_state": "NOT_AVAILABLE"
    }
