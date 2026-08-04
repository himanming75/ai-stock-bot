from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from position_manager_v2.io import load_json, write_json

DEFAULT = {
    "maximum_positions": 10,
    "maximum_symbol_weight_pct": 20.0,
    "maximum_sector_weight_pct": 40.0,
    "minimum_cash_buffer_pct": 10.0,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v236_01_to_v240_64/config/position_manager_v2_policy.json"

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
    if int(value.get("maximum_positions", 0) or 0) < 1:
        errors.append("maximum_positions must be positive.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
