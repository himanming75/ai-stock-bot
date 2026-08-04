from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paper_operations_v2.io import load_json, write_json

DEFAULT = {
    "mode": "PAPER_DRY_RUN",
    "cycle_enabled": True,
    "real_network_enabled": False,
    "paper_submission_enabled": False,
    "live_submission_enabled": False,
    "broker_write_enabled": False,
    "maximum_orders_per_cycle": 1,
    "maximum_order_quantity": 1,
    "maximum_order_notional": 100.0,
    "fill_timeout_seconds": 120,
    "maximum_retries": 2,
    "retry_delay_seconds": 5,
    "checkpoint_enabled": True,
    "reconciliation_required": True,
    "end_of_day_report_enabled": True,
}

def path(root: Path) -> Path:
    return root / "release/v221_01_to_v225_64/config/paper_operations_v2_policy.json"

def load(root: Path) -> dict[str, Any]:
    value = load_json(path(root))
    if not value:
        value = deepcopy(DEFAULT)
        value["updated_at"] = datetime.now(timezone.utc).isoformat()
        write_json(path(root), value)
    return value

def validate(value: dict[str, Any]) -> dict[str, Any]:
    errors = []
    normalized = deepcopy(DEFAULT)
    normalized.update(value)

    for key in ("live_submission_enabled", "broker_write_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key] = False

    try:
        max_orders = int(value.get("maximum_orders_per_cycle", 0))
        max_qty = int(value.get("maximum_order_quantity", 0))
        max_notional = float(value.get("maximum_order_notional", 0))
    except Exception:
        max_orders = max_qty = 0
        max_notional = 0.0

    if not 1 <= max_orders <= 5:
        errors.append("maximum_orders_per_cycle must be 1-5.")
    if not 1 <= max_qty <= 100:
        errors.append("maximum_order_quantity must be 1-100.")
    if not 1 <= max_notional <= 10000:
        errors.append("maximum_order_notional must be 1-10000.")

    normalized["maximum_orders_per_cycle"] = max_orders or 1
    normalized["maximum_order_quantity"] = max_qty or 1
    normalized["maximum_order_notional"] = max_notional or 100.0
    return {"valid": not errors, "errors": errors, "normalized": normalized}
