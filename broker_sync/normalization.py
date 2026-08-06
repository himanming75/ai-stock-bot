from __future__ import annotations


def normalize_snapshot(payload: dict) -> dict:
    if not payload:
        return {
            "accounts": [],
            "positions": [],
            "orders": [],
            "quotes": [],
        }

    if "snapshot" in payload and isinstance(
        payload["snapshot"],
        dict,
    ):
        payload = payload["snapshot"]

    if "accounts" in payload and "positions" in payload:
        return {
            "accounts": payload.get("accounts", []),
            "positions": payload.get("positions", []),
            "orders": payload.get("orders", []),
            "quotes": payload.get("quotes", []),
        }

    return {
        "accounts": payload.get("accounts", []),
        "positions": payload.get("positions", []),
        "orders": payload.get("orders", []),
        "quotes": payload.get("quotes", []),
    }


def index_positions(snapshot: dict) -> dict:
    result = {}
    for item in snapshot.get("positions", []):
        key = (
            str(item.get("broker") or ""),
            str(item.get("account_id") or ""),
            str(item.get("symbol") or "").upper(),
        )
        result[key] = item
    return result


def index_orders(snapshot: dict) -> dict:
    result = {}
    for item in snapshot.get("orders", []):
        key = (
            str(item.get("broker") or ""),
            str(item.get("account_id") or ""),
            str(item.get("order_id") or ""),
        )
        result[key] = item
    return result
