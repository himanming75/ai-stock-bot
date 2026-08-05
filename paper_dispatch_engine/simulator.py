from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def simulate_fill(
    local_order: dict[str, Any],
    market_snapshot: dict[str, Any],
    policy: dict[str, Any],
    simulated_execution_ids: set[str],
) -> dict[str, Any]:
    local_execution_id = str(local_order.get("local_execution_id", "")).strip()
    symbol = str(local_order.get("symbol", "")).strip()
    side = str(local_order.get("side", "")).upper()
    order_type = str(local_order.get("order_type", "")).upper()
    estimated_notional = local_order.get("estimated_notional")

    reference_price = market_snapshot.get("reference_price")
    available_quantity = market_snapshot.get("available_quantity")
    slippage_bps = policy.get("slippage_bps")
    fill_ratio = policy.get("fill_ratio")

    checks = {
        "local_execution_id_present": bool(local_execution_id),
        "submission_state_valid": (
            local_order.get("submission_state") == "ACCEPTED_FOR_SIMULATION"
        ),
        "paper_only": local_order.get("target_environment") == "PAPER",
        "broker_adapter_none": local_order.get("broker_adapter") == "NONE",
        "symbol_matches": market_snapshot.get("symbol") == symbol,
        "side_valid": side in {"BUY", "SELL"},
        "order_type_valid": order_type in {"MARKET", "LIMIT"},
        "notional_positive": (
            isinstance(estimated_notional, (int, float))
            and estimated_notional > 0
        ),
        "reference_price_positive": (
            isinstance(reference_price, (int, float))
            and reference_price > 0
        ),
        "available_quantity_nonnegative": (
            isinstance(available_quantity, (int, float))
            and available_quantity >= 0
        ),
        "slippage_bps_valid": (
            isinstance(slippage_bps, (int, float))
            and 0 <= slippage_bps <= 1000
        ),
        "fill_ratio_valid": (
            isinstance(fill_ratio, (int, float))
            and 0 <= fill_ratio <= 1
        ),
        "execution_not_simulated": (
            local_execution_id not in simulated_execution_ids
        ),
    }

    if not all(checks.values()):
        return {
            "state": "PAPER_EXECUTION_SIMULATION_BLOCKED",
            "approved": False,
            "checks": checks,
            "failed": [name for name, passed in checks.items() if not passed],
            "replay_detected": not checks["execution_not_simulated"],
            "fill_event": {},
            "fill_event_hash": "",
            "required_action": "DO_NOT_CREATE_FILL_EVENT",
            "actual_broker_orders_submitted": 0,
        }

    direction = 1 if side == "BUY" else -1
    fill_price = float(reference_price) * (
        1 + direction * float(slippage_bps) / 10000.0
    )

    requested_quantity = float(estimated_notional) / fill_price
    policy_quantity = requested_quantity * float(fill_ratio)
    filled_quantity = min(policy_quantity, float(available_quantity))
    remaining_quantity = max(0.0, requested_quantity - filled_quantity)

    if filled_quantity <= 0:
        fill_state = "NO_FILL"
    elif remaining_quantity > 1e-12:
        fill_state = "PARTIALLY_FILLED"
    else:
        fill_state = "FILLED"

    filled_notional = filled_quantity * fill_price

    fill_event_core = {
        "fill_event_version": "V392.11A",
        "local_execution_id": local_execution_id,
        "dispatch_id": local_order.get("dispatch_id"),
        "proposal_id": local_order.get("proposal_id"),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "reference_price": round(float(reference_price), 8),
        "slippage_bps": float(slippage_bps),
        "fill_price": round(fill_price, 8),
        "requested_quantity": round(requested_quantity, 8),
        "filled_quantity": round(filled_quantity, 8),
        "remaining_quantity": round(remaining_quantity, 8),
        "filled_notional": round(filled_notional, 8),
        "fill_state": fill_state,
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
        "broker_order_id": None,
        "simulated": True,
    }

    fill_event_id = hashlib.sha256(
        f"{local_execution_id}|{canonical_hash(fill_event_core)}".encode("utf-8")
    ).hexdigest()

    fill_event = {
        **fill_event_core,
        "fill_event_id": fill_event_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "state": "PAPER_EXECUTION_SIMULATION_ACCEPTED",
        "approved": True,
        "checks": checks,
        "failed": [],
        "replay_detected": False,
        "fill_event": fill_event,
        "fill_event_hash": canonical_hash(fill_event),
        "required_action": "ALLOW_FILL_ACCOUNTING_STAGE",
        "actual_broker_orders_submitted": 0,
    }
