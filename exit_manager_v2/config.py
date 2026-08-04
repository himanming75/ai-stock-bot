from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from exit_manager_v2.io import load_json, write_json

DEFAULT = {
    "take_profit_pct": 5.0,
    "stop_loss_pct": 3.0,
    "trailing_stop_pct": 2.0,
    "break_even_trigger_pct": 2.5,
    "maximum_holding_minutes": 390,
    "scale_out_pct": 50.0,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v241_01_to_v245_64/config/exit_manager_v2_policy.json"

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
    for key in ("take_profit_pct", "stop_loss_pct", "trailing_stop_pct", "break_even_trigger_pct"):
        try:
            number = float(value.get(key, 0))
        except Exception:
            number = -1
        if number < 0:
            errors.append(f"{key} must be non-negative.")
        normalized[key] = number
    return {"valid": not errors, "errors": errors, "normalized": normalized}
