from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from order_lifecycle_v2.io import load_json, write_json

RECOVERABLE = {"NEW", "PENDING", "ACCEPTED", "PARTIALLY_FILLED", "REPLACED"}

def build(root: Path) -> dict[str, Any]:
    state = load_json(root / "release/v231_01_to_v235_64/actual/current_order_state.json")
    recoverable = state.get("state") in RECOVERABLE
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "order_present": bool(state),
        "recoverable": recoverable,
        "order": state,
        "steps": [
            "ENABLE_EMERGENCY_STOP",
            "READ_LOCAL_ORDER_STATE",
            "READ_BROKER_ORDER_STATE",
            "MATCH_CLIENT_AND_BROKER_ORDER_IDS",
            "REPLAY_MISSING_FILL_EVENTS",
            "RECONCILE_FILLED_QUANTITY",
            "BLOCK_DUPLICATE_SUBMISSION",
            "RESUME_MONITORING_ONLY",
        ],
        "automatic_submission_allowed": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v231_01_to_v235_64/actual/order_recovery_plan.json", result)
    return result
