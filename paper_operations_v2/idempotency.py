from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from paper_operations_v2.io import load_json, write_json

def make_key(cycle_id: str, symbol: str, side: str, strategy_id: str) -> str:
    raw = f"{cycle_id}|{symbol.upper()}|{side.upper()}|{strategy_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def ledger_path(root: Path) -> Path:
    return root / "release/v221_01_to_v225_64/actual/paper_order_idempotency.json"

def register(root: Path, key: str, payload: dict[str, Any]) -> dict[str, Any]:
    ledger = load_json(ledger_path(root))
    rows = ledger.get("rows", {})
    if key in rows:
        return {"registered": False, "duplicate": True, "existing": rows[key]}
    rows[key] = payload
    ledger["rows"] = rows
    write_json(ledger_path(root), ledger)
    return {"registered": True, "duplicate": False, "record": payload}
