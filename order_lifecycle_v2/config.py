from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from order_lifecycle_v2.io import load_json, write_json

DEFAULT = {
    "mode": "ORDER_LIFECYCLE_DRY_RUN",
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
    "duplicate_window_seconds": 300,
    "maximum_fill_events": 100,
    "allow_replace": True,
    "allow_cancel": True,
    "recovery_enabled": True,
}

def path(root: Path) -> Path:
    return root / "release/v231_01_to_v235_64/config/order_lifecycle_v2_policy.json"

def load(root: Path) -> dict[str, Any]:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path(root), value)
    return value

def validate(value: dict[str, Any]) -> dict[str, Any]:
    errors = []
    normalized = deepcopy(DEFAULT)
    normalized.update(value)
    for key in ("paper_submission_enabled", "live_submission_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key] = False
    try:
        window = int(value.get("duplicate_window_seconds", 0))
    except Exception:
        window = 0
    if not 1 <= window <= 86400:
        errors.append("duplicate_window_seconds must be 1-86400.")
    normalized["duplicate_window_seconds"] = window or 300
    return {"valid": not errors, "errors": errors, "normalized": normalized}
