from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"orders": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_registry(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reserve(
    path: Path,
    client_order_id: str,
    request_hash: str,
) -> dict[str, Any]:
    registry = load_registry(path)
    orders = registry.setdefault("orders", {})
    existing = orders.get(client_order_id)
    if existing is not None:
        if existing.get("request_hash") == request_hash:
            raise ValueError("DUPLICATE_CLIENT_ORDER_ID")
        raise ValueError("CLIENT_ORDER_ID_HASH_CONFLICT")

    record = {
        "client_order_id": client_order_id,
        "request_hash": request_hash,
        "state": "RESERVED",
        "reserved_at": datetime.now(timezone.utc).isoformat(),
    }
    orders[client_order_id] = record
    save_registry(path, registry)
    return record


def update(
    path: Path,
    client_order_id: str,
    **changes: Any,
) -> None:
    registry = load_registry(path)
    orders = registry.setdefault("orders", {})
    if client_order_id not in orders:
        raise KeyError("CLIENT_ORDER_ID_NOT_RESERVED")
    orders[client_order_id].update(changes)
    save_registry(path, registry)


def count_for_date(path: Path, utc_date: str) -> int:
    registry = load_registry(path)
    return sum(
        1
        for value in registry.get("orders", {}).values()
        if str(value.get("reserved_at", "")).startswith(utc_date)
        and value.get("state") not in {"REJECTED_BEFORE_SUBMISSION"}
    )
