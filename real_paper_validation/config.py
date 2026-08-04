from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from real_paper_validation.io import load_json, write_json

DEFAULT = {
    "paper_base_url": "https://paper-api.alpaca.markets",
    "paper_read_enabled": False,
    "micro_paper_order_enabled": False,
    "maximum_orders_per_run": 1,
    "maximum_quantity": 1,
    "maximum_notional": 100.0,
    "require_market_open": True,
    "require_explicit_confirmation": True,
    "confirmation_phrase": "ENABLE_ONE_MICRO_PAPER_ORDER",
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False
}

def path(root: Path) -> Path:
    return root / "release/v301_01_to_v305_64/config/real_paper_validation_policy.json"

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
    for key in ("live_submission_enabled", "live_network_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain false.")
    if int(value.get("maximum_orders_per_run", 0)) != 1:
        errors.append("maximum_orders_per_run must remain 1.")
    if int(value.get("maximum_quantity", 0)) != 1:
        errors.append("maximum_quantity must remain 1.")
    return {"valid": not errors, "errors": errors}
