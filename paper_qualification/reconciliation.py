from __future__ import annotations
from typing import Any

def _by_symbol(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("symbol")): row for row in rows if row.get("symbol")}

def compare(internal: dict[str, Any], broker: dict[str, Any]) -> dict[str, Any]:
    mismatches = []
    account_fields = ("cash", "equity", "buying_power")
    for field in account_fields:
        left = round(float(internal.get("account", {}).get(field, 0) or 0), 2)
        right = round(float(broker.get("account", {}).get(field, 0) or 0), 2)
        if left != right:
            mismatches.append({"type": "ACCOUNT_FIELD", "field": field, "internal": left, "broker": right})

    internal_positions = _by_symbol(internal.get("positions", []))
    broker_positions = _by_symbol(broker.get("positions", []))
    for symbol in sorted(set(internal_positions) | set(broker_positions)):
        left = internal_positions.get(symbol, {})
        right = broker_positions.get(symbol, {})
        left_qty = float(left.get("qty", 0) or 0)
        right_qty = float(right.get("qty", 0) or 0)
        if left_qty != right_qty:
            mismatches.append({"type": "POSITION_QTY", "symbol": symbol, "internal": left_qty, "broker": right_qty})

    internal_orders = {str(row.get("client_order_id")): row for row in internal.get("orders", [])}
    broker_orders = {str(row.get("client_order_id")): row for row in broker.get("orders", [])}
    for order_id in sorted(set(internal_orders) | set(broker_orders)):
        left = internal_orders.get(order_id, {})
        right = broker_orders.get(order_id, {})
        if str(left.get("status", "")) != str(right.get("status", "")):
            mismatches.append({
                "type": "ORDER_STATUS",
                "client_order_id": order_id,
                "internal": left.get("status"),
                "broker": right.get("status"),
            })

    checks = {
        "account_match": not any(x["type"] == "ACCOUNT_FIELD" for x in mismatches),
        "positions_match": not any(x["type"] == "POSITION_QTY" for x in mismatches),
        "orders_match": not any(x["type"] == "ORDER_STATUS" for x in mismatches),
    }
    return {"passed": not mismatches, "checks": checks, "mismatches": mismatches}
