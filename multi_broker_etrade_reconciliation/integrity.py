from __future__ import annotations
from collections import Counter


def validate_snapshot(snapshot: dict) -> dict:
    issues = []

    if not isinstance(snapshot, dict):
        return {
            "passed": False,
            "issues": ["SNAPSHOT_NOT_OBJECT"],
        }

    for key in ("accounts", "positions", "orders"):
        if key not in snapshot:
            issues.append(f"MISSING_SECTION:{key}")
        elif not isinstance(snapshot[key], list):
            issues.append(f"SECTION_NOT_LIST:{key}")

    accounts = snapshot.get("accounts", [])
    account_ids = [
        str(item.get("account_id") or "")
        for item in accounts
        if isinstance(item, dict)
    ]
    duplicates = [
        value
        for value, count in Counter(account_ids).items()
        if value and count > 1
    ]
    for value in duplicates:
        issues.append(f"DUPLICATE_ACCOUNT_ID:{value}")

    orders = snapshot.get("orders", [])
    order_ids = [
        str(item.get("order_id") or "")
        for item in orders
        if isinstance(item, dict)
    ]
    duplicate_orders = [
        value
        for value, count in Counter(order_ids).items()
        if value and count > 1
    ]
    for value in duplicate_orders:
        issues.append(f"DUPLICATE_ORDER_ID:{value}")

    return {
        "passed": not issues,
        "issues": issues,
    }
