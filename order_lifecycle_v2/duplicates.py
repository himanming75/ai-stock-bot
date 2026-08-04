from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from order_lifecycle_v2.io import load_json, write_json

def key(order: dict[str, Any]) -> str:
    return "|".join([
        str(order.get("symbol", "")).upper(),
        str(order.get("side", "")).upper(),
        str(order.get("quantity", "")),
        str(order.get("strategy_id", "")),
    ])

def register(root: Path, order: dict[str, Any]) -> dict[str, Any]:
    path = root / "release/v231_01_to_v235_64/actual/order_duplicate_registry.json"
    registry = load_json(path)
    rows = registry.get("rows", {})
    duplicate_key = key(order)
    if duplicate_key in rows:
        return {"duplicate": True, "existing": rows[duplicate_key], "duplicate_key": duplicate_key}
    rows[duplicate_key] = {
        "client_order_id": order.get("client_order_id"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    registry["rows"] = rows
    write_json(path, registry)
    return {"duplicate": False, "duplicate_key": duplicate_key}
