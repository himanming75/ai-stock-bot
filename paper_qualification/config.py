from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from paper_qualification.io import load_json, write_json

DEFAULT = {
    "paper_read_enabled": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False,
    "minimum_sessions": 10,
    "minimum_cycles": 100,
    "minimum_reconciliation_pass_rate_pct": 99.0,
    "maximum_unresolved_mismatches": 0,
    "maximum_duplicate_orders": 0,
    "maximum_recovery_failures": 0,
    "minimum_order_state_coverage_pct": 80.0,
    "maximum_daily_drawdown_pct": 5.0,
    "minimum_profit_factor": 1.10,
    "minimum_win_rate_pct": 45.0,
    "paper_base_url": "https://paper-api.alpaca.markets"
}

def path(root: Path) -> Path:
    return root / "release/v291_01_to_v300_64/config/paper_qualification_policy.json"

def load(root: Path) -> dict:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path(root), value)
    return value

def validate(value: dict) -> dict:
    errors = []
    if value.get("paper_base_url") != "https://paper-api.alpaca.markets":
        errors.append("Only Alpaca Paper endpoint is allowed.")
    for key in ("paper_submission_enabled", "live_submission_enabled", "live_network_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain false.")
    return {"valid": not errors, "errors": errors}
