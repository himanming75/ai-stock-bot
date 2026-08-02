from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_validation_certificate_payload(
    root: Path,
) -> dict[str, Any]:
    path = (
        root / "release/op5_09_to_op5_12/actual/"
        "validation_certificate_dashboard_state.json"
    )
    if not path.exists():
        return {"certificate_state": "NOT_AVAILABLE"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"certificate_state": "NOT_AVAILABLE"}
    return payload if isinstance(payload, dict) else {
        "certificate_state": "NOT_AVAILABLE"
    }
