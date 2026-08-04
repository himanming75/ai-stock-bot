from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from windows_autostart_recovery.io import load_json, write_json

DEFAULT = {
    "autostart_registration_enabled": False,
    "supervisor_enabled": False,
    "restart_on_failure": True,
    "maximum_restarts": 5,
    "restart_backoff_seconds": 30,
    "stale_lock_minutes": 30,
    "log_retention_days": 30,
    "task_name": "AIStockBot-AutonomousPaper",
    "run_only_when_user_logged_on": True,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v266_01_to_v270_64/config/windows_autostart_recovery_policy.json"

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
    for key in ("live_submission_enabled", "live_network_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain false.")
        normalized[key] = False
    if int(value.get("maximum_restarts", -1)) < 0:
        errors.append("maximum_restarts must be non-negative.")
    if int(value.get("stale_lock_minutes", 0)) < 1:
        errors.append("stale_lock_minutes must be positive.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
