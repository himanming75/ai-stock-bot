from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from real_paper_data_collection.io import load_json, write_json

DEFAULT = {
    "paper_base_url": "https://paper-api.alpaca.markets",
    "collector_enabled": False,
    "paper_read_enabled": False,
    "paper_submission_enabled": False,
    "cycle_interval_seconds": 30,
    "market_closed_poll_seconds": 120,
    "maximum_cycles_per_run": 480,
    "maximum_runtime_minutes": 480,
    "stop_after_market_close": True,
    "maximum_new_orders_per_day": 0,
    "maximum_new_order_notional": 5.0,
    "collect_account": True,
    "collect_clock": True,
    "collect_positions": True,
    "collect_open_orders": True,
    "collect_closed_orders": True,
    "closed_order_limit": 100,
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False
}

def path(root: Path) -> Path:
    return root / "release/v311_01_to_v320_64/config/real_paper_data_collection_policy.json"

def load(root: Path) -> dict:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        write_json(path(root), value)
    return value

def validate(value: dict) -> dict:
    errors = []
    if value.get("paper_base_url") != "https://paper-api.alpaca.markets":
        errors.append("Only Alpaca Paper endpoint is allowed.")
    if int(value.get("cycle_interval_seconds", 0)) < 10:
        errors.append("cycle_interval_seconds must be at least 10.")
    if int(value.get("maximum_new_orders_per_day", 0)) != 0:
        errors.append("V311-V320 must remain monitor-only with zero new orders.")
    for key in (
        "paper_submission_enabled",
        "live_submission_enabled",
        "live_network_enabled",
        "broker_write_enabled",
    ):
        if value.get(key) is not False:
            errors.append(f"{key} must remain false.")
    return {"valid": not errors, "errors": errors}
