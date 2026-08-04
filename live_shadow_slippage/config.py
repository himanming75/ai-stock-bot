from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from live_shadow_slippage.io import load_json, write_json

DEFAULT = {
    "mode": "LIVE_SHADOW_READ_ONLY",
    "real_live_read_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
    "maximum_spread_pct": 0.50,
    "maximum_slippage_pct": 0.25,
    "maximum_quote_age_seconds": 15,
    "minimum_buying_power_buffer_pct": 20.0,
    "minimum_qualification_score": 80.0,
    "estimated_fee_per_order": 0.0,
    "qualification_history_required": 20,
}

def path(root: Path) -> Path:
    return root / "release/v226_01_to_v230_64/config/live_shadow_policy.json"

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
    for key in ("live_submission_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key] = False
    for key in ("maximum_spread_pct", "maximum_slippage_pct", "minimum_buying_power_buffer_pct"):
        try:
            number = float(value.get(key, DEFAULT[key]))
        except Exception:
            number = -1
        if number < 0:
            errors.append(f"{key} must be non-negative.")
        normalized[key] = number
    return {"valid": not errors, "errors": errors, "normalized": normalized}
