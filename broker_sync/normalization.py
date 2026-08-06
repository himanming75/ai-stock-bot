from __future__ import annotations
from typing import Any


UNIVERSAL_KEYS = {
    "accounts",
    "positions",
    "orders",
    "quotes",
}


def _as_dict_list(value: Any) -> list[dict]:
    """
    Convert mixed API/file values to a list containing only dictionaries.

    Accepted input:
    - None
    - dict
    - list/tuple containing dicts, lists, strings, numbers
    - nested response containers

    Primitive values are ignored because reconciliation requires structured
    records with named fields.
    """
    if value is None:
        return []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, (list, tuple)):
        result: list[dict] = []
        for item in value:
            result.extend(_as_dict_list(item))
        return result

    return []


def _find_named_values(
    value: Any,
    names: set[str],
) -> list[Any]:
    """
    Recursively locate values stored under any requested key.

    This supports actual broker validation files whose top-level structure can
    contain wrapper objects such as snapshot, data, OrdersResponse, Order,
    orders, or broker/account keyed dictionaries.
    """
    found: list[Any] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in names:
                found.append(item)
            found.extend(
                _find_named_values(item, names)
            )
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(
                _find_named_values(item, names)
            )

    return found


def _looks_like_universal_order(item: dict) -> bool:
    return any(
        key in item
        for key in (
            "order_id",
            "orderId",
            "status",
            "symbol",
            "side",
            "order_type",
            "orderType",
        )
    )


def _extract_orders(value: Any) -> list[dict]:
    """
    Extract order dictionaries from universal snapshots and actual E*TRADE
    validation output.

    String status values and dictionary keys such as account IDs are never
    returned as orders.
    """
    direct = _as_dict_list(value)

    result: list[dict] = []
    seen: set[int] = set()

    def add(item: dict) -> None:
        marker = id(item)
        if marker in seen:
            return
        seen.add(marker)
        if _looks_like_universal_order(item):
            result.append(item)

    for item in direct:
        add(item)

    named_values = _find_named_values(
        value,
        {
            "orders",
            "order",
            "orderdetail",
        },
    )
    for named in named_values:
        for item in _as_dict_list(named):
            add(item)

    return result


def _extract_collection(
    payload: dict,
    name: str,
) -> list[dict]:
    direct = payload.get(name)
    direct_items = _as_dict_list(direct)

    if direct_items:
        return direct_items

    found = _find_named_values(
        payload,
        {name.lower()},
    )
    result: list[dict] = []
    for value in found:
        result.extend(_as_dict_list(value))
    return result


def normalize_snapshot(payload: dict) -> dict:
    if not isinstance(payload, dict) or not payload:
        return {
            "accounts": [],
            "positions": [],
            "orders": [],
            "quotes": [],
        }

    candidates: list[dict] = [payload]

    snapshot = payload.get("snapshot")
    if isinstance(snapshot, dict):
        candidates.insert(0, snapshot)

    portal_snapshot = payload.get(
        "portal_snapshot"
    )
    if isinstance(portal_snapshot, dict):
        candidates.insert(0, portal_snapshot)

    for candidate in candidates:
        if any(
            key in candidate
            for key in UNIVERSAL_KEYS
        ):
            return {
                "accounts": _extract_collection(
                    candidate,
                    "accounts",
                ),
                "positions": _extract_collection(
                    candidate,
                    "positions",
                ),
                "orders": _extract_orders(
                    candidate.get("orders")
                ),
                "quotes": _extract_collection(
                    candidate,
                    "quotes",
                ),
            }

    return {
        "accounts": _extract_collection(
            payload,
            "accounts",
        ),
        "positions": _extract_collection(
            payload,
            "positions",
        ),
        "orders": _extract_orders(payload),
        "quotes": _extract_collection(
            payload,
            "quotes",
        ),
    }


def index_positions(snapshot: dict) -> dict:
    result = {}
    for item in snapshot.get("positions", []):
        if not isinstance(item, dict):
            continue
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
        if not isinstance(item, dict):
            continue
        key = (
            str(item.get("broker") or ""),
            str(item.get("account_id") or ""),
            str(
                item.get("order_id")
                or item.get("orderId")
                or ""
            ),
        )
        result[key] = item
    return result
