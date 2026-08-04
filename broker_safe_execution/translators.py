from __future__ import annotations
from typing import Any

def translate_intent(
    intent: dict[str, Any],
    adapter_name: str,
) -> dict[str, Any]:
    common={
        "client_order_id":intent.get("intent_id"),
        "symbol":intent.get("symbol"),
        "side":intent.get("side"),
        "quantity":intent.get("quantity"),
        "order_type":intent.get("order_type"),
        "time_in_force":intent.get("time_in_force"),
        "limit_price":intent.get("limit_price"),
    }
    if adapter_name=="ALPACA_READ_ONLY":
        payload={
            "client_order_id":common["client_order_id"],
            "symbol":common["symbol"],
            "side":common["side"].lower(),
            "qty":common["quantity"],
            "type":common["order_type"].lower(),
            "time_in_force":common["time_in_force"].lower(),
            "limit_price":common["limit_price"],
        }
    elif adapter_name=="IBKR_READ_ONLY":
        payload={
            "cOID":common["client_order_id"],
            "ticker":common["symbol"],
            "action":common["side"],
            "quantity":common["quantity"],
            "orderType":common["order_type"],
            "tif":common["time_in_force"],
            "price":common["limit_price"],
        }
    elif adapter_name=="ETRADE_READ_ONLY":
        payload={
            "clientOrderId":common["client_order_id"],
            "symbol":common["symbol"],
            "orderAction":common["side"],
            "quantity":common["quantity"],
            "priceType":common["order_type"],
            "orderTerm":common["time_in_force"],
            "limitPrice":common["limit_price"],
        }
    else:
        payload=common
    return {
        "adapter_name":adapter_name,
        "intent_id":intent.get("intent_id"),
        "payload":payload,
        "translation_only":True,
        "submitted":False,
    }
