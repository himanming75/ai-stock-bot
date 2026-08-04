from __future__ import annotations
from typing import Any

def detect_drift(
    reconciliation: dict[str, Any],
    broker_orders: list[dict[str, Any]],
) -> dict[str, Any]:
    events=[]
    for name,value in reconciliation.get("account",{}).items():
        if not value.get("passed"):
            events.append({
                "category":"ACCOUNT",
                "field":name,
                "difference":value.get("difference"),
            })
    for symbol,value in reconciliation.get("positions",{}).items():
        if not value.get("passed"):
            events.append({
                "category":"POSITION",
                "symbol":symbol,
                "quantity_difference":value.get(
                    "quantity",{}
                ).get("difference"),
                "market_value_difference":value.get(
                    "market_value",{}
                ).get("difference"),
            })
    open_orders=[
        row for row in broker_orders
        if row.get("status") in {
            "NEW","ACCEPTED","PARTIALLY_FILLED","PENDING_NEW"
        }
    ]
    if open_orders:
        events.append({
            "category":"OPEN_BROKER_ORDERS",
            "count":len(open_orders),
        })
    return {
        "drift_detected":bool(events),
        "drift_event_count":len(events),
        "events":events,
        "open_broker_order_count":len(open_orders),
    }
