from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from execution_optimizer.io import load_json, write_json

DEFAULT = {
    "maximum_spread_pct": 0.20,
    "maximum_quote_age_seconds": 10,
    "maximum_expected_slippage_pct": 0.15,
    "minimum_fill_probability_pct": 65.0,
    "limit_offset_bps": 2.0,
    "retry_limit": 2,
    "retry_delay_seconds": 5,
    "partial_fill_timeout_seconds": 90,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v251_01_to_v255_64/config/execution_optimizer_policy.json"

def load(root: Path) -> dict:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path(root), value)
    return value

def validate(value: dict) -> dict:
    errors = []
    normalized = deepcopy(DEFAULT)
    normalized.update(value)
    for key in ("paper_submission_enabled", "live_submission_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key] = False
    if int(value.get("retry_limit", -1)) < 0:
        errors.append("retry_limit must be non-negative.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
