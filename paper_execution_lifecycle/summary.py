from __future__ import annotations
from collections import Counter


def summarize(orders: list[dict], events: list[dict]) -> dict:
    states = Counter(str(item.get("status", "unknown")) for item in orders)
    event_types = Counter(str(item.get("type", "UNKNOWN")) for item in events)
    return {
        "order_count": len(orders),
        "order_states": dict(sorted(states.items())),
        "event_count": len(events),
        "event_types": dict(sorted(event_types.items())),
        "filled_orders": states.get("filled", 0),
        "partially_filled_orders": states.get("partially_filled", 0),
        "canceled_orders": states.get("canceled", 0),
        "rejected_orders": states.get("rejected", 0),
    }
