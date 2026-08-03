from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_shadow_portfolio_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v81_09_to_v81_12/actual/"
        / "shadow_portfolio_dashboard_state.json"
    )
    if not path.exists():
        return {"portfolio_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"portfolio_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "portfolio_state": "NOT_AVAILABLE"
    }
