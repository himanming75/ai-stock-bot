from __future__ import annotations
from typing import Any


def build_events(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev = {item.get("id"): item for item in previous if item.get("id")}
    events: list[dict[str, Any]] = []

    for item in current:
        order_id = item.get("id")
        if not order_id:
            continue
        old = prev.get(order_id)

        if old is None:
            events.append({
                "type": "ORDER_DISCOVERED",
                "order_id": order_id,
                "client_order_id": item.get("client_order_id"),
                "symbol": item.get("symbol"),
                "current_status": item.get("status"),
            })
            continue

        if old.get("status") != item.get("status"):
            events.append({
                "type": "ORDER_STATUS_CHANGED",
                "order_id": order_id,
                "client_order_id": item.get("client_order_id"),
                "symbol": item.get("symbol"),
                "previous_status": old.get("status"),
                "current_status": item.get("status"),
            })

        if str(old.get("filled_qty")) != str(item.get("filled_qty")):
            events.append({
                "type": "FILLED_QTY_CHANGED",
                "order_id": order_id,
                "client_order_id": item.get("client_order_id"),
                "symbol": item.get("symbol"),
                "previous_filled_qty": old.get("filled_qty"),
                "current_filled_qty": item.get("filled_qty"),
            })

        if str(old.get("filled_avg_price")) != str(item.get("filled_avg_price")):
            events.append({
                "type": "FILL_PRICE_CHANGED",
                "order_id": order_id,
                "client_order_id": item.get("client_order_id"),
                "symbol": item.get("symbol"),
                "previous_filled_avg_price": old.get("filled_avg_price"),
                "current_filled_avg_price": item.get("filled_avg_price"),
            })

    return events
