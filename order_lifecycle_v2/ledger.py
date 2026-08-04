from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from order_lifecycle_v2.io import append_jsonl

def event(root: Path, order: dict[str, Any], event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    row = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "client_order_id": order.get("client_order_id"),
        "broker_order_id": order.get("broker_order_id"),
        "event_type": event_type,
        "state": order.get("state"),
        "filled_quantity": order.get("filled_quantity", 0),
        "remaining_quantity": order.get("remaining_quantity", order.get("quantity", 0)),
        "average_fill_price": order.get("average_fill_price", 0),
        "details": details or {},
        "actual_live_orders_submitted": 0,
    }
    append_jsonl(root / "release/v231_01_to_v235_64/actual/order_lifecycle_v2_ledger.jsonl", row)
    return row
