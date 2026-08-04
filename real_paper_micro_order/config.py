from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from real_paper_micro_order.io import load_json, write_json

DEFAULT = {
    "paper_base_url": "https://paper-api.alpaca.markets",
    "micro_order_enabled": False,
    "symbol": "SPY",
    "side": "buy",
    "order_type": "market",
    "time_in_force": "day",
    "notional": 1.0,
    "maximum_notional": 5.0,
    "maximum_orders_lifetime": 1,
    "require_market_open": True,
    "require_no_open_orders": True,
    "require_explicit_confirmation": True,
    "confirmation_phrase": "ENABLE_ONE_DOLLAR_PAPER_ORDER",
    "live_submission_enabled": False,
    "live_network_enabled": False,
    "broker_write_enabled": False
}

def path(root: Path) -> Path:
    return root / "release/v306_01_to_v310_64/config/real_paper_micro_order_policy.json"

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
    if str(value.get("order_type")).lower() != "market":
        errors.append("Only market order is allowed for this validation.")
    if str(value.get("time_in_force")).lower() != "day":
        errors.append("Only DAY time in force is allowed.")
    notional = float(value.get("notional", 0) or 0)
    maximum = float(value.get("maximum_notional", 0) or 0)
    if notional <= 0 or notional > maximum or maximum > 5.0:
        errors.append("Micro Paper notional must be positive and no more than $5.")
    if int(value.get("maximum_orders_lifetime", 0)) != 1:
        errors.append("maximum_orders_lifetime must remain 1.")
    for key in ("live_submission_enabled", "live_network_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain false.")
    return {"valid": not errors, "errors": errors}
