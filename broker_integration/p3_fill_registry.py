from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def fill_key(order: dict[str, Any]) -> str:
    raw = "|".join([
        str(order.get("id", "")),
        str(order.get("filled_qty", "0")),
        str(order.get("filled_avg_price", "")),
        str(order.get("filled_at", "")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"fills": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_registry(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def register_fill(
    path: Path,
    order: dict[str, Any],
) -> tuple[bool, str]:
    key = fill_key(order)
    registry = load_registry(path)
    fills = registry.setdefault("fills", {})
    if key in fills:
        return False, key

    fills[key] = {
        "fill_key": key,
        "order_id": order.get("id"),
        "client_order_id": order.get("client_order_id"),
        "symbol": order.get("symbol"),
        "side": order.get("side"),
        "filled_qty": order.get("filled_qty"),
        "filled_avg_price": order.get("filled_avg_price"),
        "filled_at": order.get("filled_at"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    save_registry(path, registry)
    return True, key
