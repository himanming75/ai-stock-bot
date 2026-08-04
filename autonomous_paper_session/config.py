from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_session.io import load_json, write_json

DEFAULT = {
    "session_runner_enabled": False,
    "allow_real_paper_network": False,
    "cycle_interval_seconds": 30,
    "market_closed_poll_seconds": 60,
    "maximum_cycles_per_session": 1000,
    "maximum_runtime_minutes": 480,
    "maximum_consecutive_errors": 5,
    "error_backoff_seconds": 30,
    "stop_after_market_close": True,
    "single_instance_required": True,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False,
}

def path(root: Path) -> Path:
    return root / "release/v261_01_to_v265_64/config/session_runner_policy.json"

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
    if int(value.get("cycle_interval_seconds", 0) or 0) < 5:
        errors.append("cycle_interval_seconds must be at least 5.")
    if int(value.get("maximum_cycles_per_session", 0) or 0) < 1:
        errors.append("maximum_cycles_per_session must be positive.")
    return {"valid": not errors, "errors": errors, "normalized": normalized}
