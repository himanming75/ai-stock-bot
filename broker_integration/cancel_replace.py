from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .io import append_jsonl


def cancel_paper_order(
    http: Any,
    order_id: str,
    ledger_path,
) -> dict[str, Any]:
    if not order_id.strip():
        raise ValueError("ORDER_ID_REQUIRED")
    response, request_id = http.cancel_order(order_id)
    result = {
        "stage": "P2",
        "operation": "CANCEL",
        "order_id": order_id,
        "request_id": request_id,
        "response": response,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted": 0,
    }
    append_jsonl(ledger_path, result)
    return result


def replace_paper_order(
    http: Any,
    order_id: str,
    *,
    qty: str | None = None,
    time_in_force: str | None = None,
    limit_price: str | None = None,
    ledger_path,
) -> dict[str, Any]:
    if not order_id.strip():
        raise ValueError("ORDER_ID_REQUIRED")
    payload = {
        key: value
        for key, value in {
            "qty": qty,
            "time_in_force": time_in_force,
            "limit_price": limit_price,
        }.items()
        if value is not None
    }
    if not payload:
        raise ValueError("REPLACE_PAYLOAD_REQUIRED")
    response, request_id = http.replace_order(order_id, payload)
    result = {
        "stage": "P2",
        "operation": "REPLACE",
        "order_id": order_id,
        "request_id": request_id,
        "payload": payload,
        "response": response,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted": 0,
    }
    append_jsonl(ledger_path, result)
    return result
