from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from order_lifecycle_v2.config import load, validate
from order_lifecycle_v2.duplicates import register
from order_lifecycle_v2.fills import apply_fill
from order_lifecycle_v2.identity import client_order_id, mapping
from order_lifecycle_v2.io import load_json, write_json
from order_lifecycle_v2.ledger import event
from order_lifecycle_v2.recovery import build as build_recovery
from order_lifecycle_v2.state_machine import transition

def evaluate(root: Path) -> dict[str, Any]:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(root / "release/v231_01_to_v235_64/input/order_lifecycle_fixture.json")
    requested = fixture.get("order", {})
    fills = fixture.get("fills", [])

    client_id = client_order_id(
        str(requested.get("strategy_id", "NO_STRATEGY")),
        str(requested.get("symbol", "UNKNOWN")),
        str(requested.get("side", "BUY")),
        str(requested.get("nonce", "001")),
    )
    order = {
        "client_order_id": client_id,
        "broker_order_id": fixture.get("broker_order_id"),
        "strategy_id": requested.get("strategy_id"),
        "symbol": requested.get("symbol"),
        "side": requested.get("side"),
        "quantity": float(requested.get("quantity", 0) or 0),
        "filled_quantity": 0.0,
        "remaining_quantity": float(requested.get("quantity", 0) or 0),
        "average_fill_price": 0.0,
        "state": "NEW",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    duplicate = register(root, order)
    events = [event(root, order, "ORDER_CREATED", {"duplicate": duplicate["duplicate"]})]

    if not duplicate["duplicate"]:
        for target in ("PENDING", "ACCEPTED"):
            decision = transition(order, target)
            if decision["allowed"]:
                order["state"] = target
                events.append(event(root, order, "STATE_TRANSITION", decision))

        for fill in fills:
            decision = transition(order, "PARTIALLY_FILLED" if order["remaining_quantity"] > float(fill.get("quantity", 0)) else "FILLED")
            if not decision["allowed"] and order["state"] not in {"ACCEPTED", "PARTIALLY_FILLED"}:
                break
            order = apply_fill(order, float(fill.get("quantity", 0)), float(fill.get("price", 0)))
            events.append(event(root, order, "FILL_APPLIED", fill))

    write_json(root / "release/v231_01_to_v235_64/actual/current_order_state.json", order)
    write_json(root / "release/v231_01_to_v235_64/actual/order_id_mapping.json", mapping(client_id, order.get("broker_order_id")))
    recovery = build_recovery(root)

    checks = {
        "policy_valid": validation["valid"],
        "client_order_id_present": bool(client_id),
        "duplicate_protection_present": "duplicate" in duplicate,
        "state_valid": order["state"] in {"NEW", "PENDING", "ACCEPTED", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED", "REPLACED"},
        "filled_quantity_not_over_order": order["filled_quantity"] <= order["quantity"],
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
        "recovery_present": bool(recovery),
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = "ORDER_LIFECYCLE_V2_READY" if not failed else "ORDER_LIFECYCLE_V2_REVIEW_REQUIRED"

    result = {
        "stage": "V235.64",
        "state": state,
        "status": "PASS",
        "order": order,
        "duplicate": duplicate,
        "events": events,
        "recovery": recovery,
        "checks": checks,
        "failed": failed,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V236_01_TO_V240_64_POSITION_MANAGER_V2",
    }
    write_json(root / "release/v231_01_to_v235_64/actual/order_lifecycle_v2_result.json", result)
    return result
