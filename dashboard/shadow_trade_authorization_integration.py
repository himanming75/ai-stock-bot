
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_shadow_trade_authorization_payload(
    root: Path,
) -> dict[str, Any]:
    path = (
        root
        / "release/v82_17_to_v82_20/actual/"
        / "shadow_trade_authorization_dashboard_state.json"
    )
    if not path.exists():
        return {"authorization_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"authorization_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "authorization_state": "NOT_AVAILABLE"
    }
