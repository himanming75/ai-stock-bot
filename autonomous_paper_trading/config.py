from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_trading.io import load_json, write_json

DEFAULT = {
    "mode": "AUTONOMOUS_PAPER",
    "autonomous_cycle_enabled": False,
    "real_paper_read_enabled": True,
    "real_paper_submission_enabled": False,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False,
    "maximum_orders_per_session": 1,
    "maximum_order_quantity": 1,
    "maximum_order_notional": 100.0,
    "cycle_interval_seconds": 30,
    "maximum_cycles_per_run": 1,
    "require_market_open": True,
    "require_confirmation_token": True,
    "confirmation_phrase": "ENABLE_AUTONOMOUS_PAPER",
    "paper_base_url": "https://paper-api.alpaca.markets",
}

def path(root: Path) -> Path:
    return root / "release/v256_01_to_v260_64/config/autonomous_paper_policy.json"

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
    if value.get("live_submission_enabled") is not False:
        errors.append("live_submission_enabled must remain false.")
    if value.get("live_network_enabled") is not False:
        errors.append("live_network_enabled must remain false.")
    if value.get("broker_write_enabled") is not False:
        errors.append("broker_write_enabled must remain false.")
    if value.get("paper_base_url") != "https://paper-api.alpaca.markets":
        errors.append("paper_base_url must be Alpaca Paper.")
    for key in ("live_submission_enabled", "live_network_enabled", "broker_write_enabled"):
        normalized[key] = False
    return {"valid": not errors, "errors": errors, "normalized": normalized}
