from __future__ import annotations
import hashlib
import json
from typing import Any


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    account = snapshot.get("account", {})
    positions = snapshot.get("positions", [])
    open_orders = snapshot.get("open_orders", [])
    clock = snapshot.get("clock", {})
    assets = snapshot.get("assets", {})

    checks = {
        "account_present": isinstance(account, dict) and bool(account),
        "account_status_present": bool(account.get("status")),
        "equity_present": "equity" in account,
        "buying_power_present": "buying_power" in account,
        "positions_list": isinstance(positions, list),
        "position_symbols_present": all(
            bool(item.get("symbol")) for item in positions
        ),
        "open_orders_list": isinstance(open_orders, list),
        "order_ids_present": all(
            bool(item.get("id")) for item in open_orders
        ),
        "clock_present": isinstance(clock, dict) and "is_open" in clock,
        "assets_present": isinstance(assets, dict) and bool(assets),
        "assets_tradability_present": all(
            "tradable" in value and "fractionable" in value
            for value in assets.values()
        ),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
        "snapshot_hash": canonical_hash(snapshot),
    }
