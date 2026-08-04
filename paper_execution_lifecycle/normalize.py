from __future__ import annotations
from typing import Any


LIFECYCLE_STATES = {
    "accepted", "new", "pending_new", "partially_filled", "filled",
    "done_for_day", "canceled", "expired", "replaced", "pending_cancel",
    "pending_replace", "stopped", "rejected", "suspended", "calculated"
}


def normalize_order(order: dict[str, Any]) -> dict[str, Any]:
    status = str(order.get("status", "unknown")).lower()
    return {
        "id": str(order.get("id", "")),
        "client_order_id": str(order.get("client_order_id", "")),
        "symbol": str(order.get("symbol", "")).upper(),
        "side": str(order.get("side", "")).lower(),
        "type": str(order.get("type", "")).lower(),
        "time_in_force": str(order.get("time_in_force", "")).lower(),
        "status": status,
        "status_known": status in LIFECYCLE_STATES,
        "qty": order.get("qty"),
        "notional": order.get("notional"),
        "filled_qty": order.get("filled_qty"),
        "filled_avg_price": order.get("filled_avg_price"),
        "submitted_at": order.get("submitted_at"),
        "filled_at": order.get("filled_at"),
        "canceled_at": order.get("canceled_at"),
        "expired_at": order.get("expired_at"),
        "failed_at": order.get("failed_at"),
        "replaced_at": order.get("replaced_at"),
        "replaced_by": order.get("replaced_by"),
        "replaces": order.get("replaces"),
    }


def normalize_position(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": str(position.get("symbol", "")).upper(),
        "qty": str(position.get("qty", "0")),
        "avg_entry_price": str(position.get("avg_entry_price", "0")),
        "market_value": str(position.get("market_value", "0")),
        "cost_basis": str(position.get("cost_basis", "0")),
        "unrealized_pl": str(position.get("unrealized_pl", "0")),
        "side": str(position.get("side", "")),
    }
