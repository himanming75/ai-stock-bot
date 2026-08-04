from __future__ import annotations
import hashlib
from pathlib import Path
from autonomous_paper_trading.io import load_json, write_json

def make_key(session_id: str, plan: dict) -> str:
    raw = "|".join([
        session_id,
        str(plan.get("symbol", "")).upper(),
        str(plan.get("action", "")).upper(),
        str(plan.get("quantity", "")),
        str(plan.get("limit_price", "")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def register(root: Path, key: str, value: dict) -> dict:
    path = root / "release/v256_01_to_v260_64/actual/autonomous_paper_idempotency.json"
    ledger = load_json(path)
    rows = ledger.get("rows", {})
    if key in rows:
        return {"registered": False, "duplicate": True, "existing": rows[key]}
    rows[key] = value
    ledger["rows"] = rows
    write_json(path, ledger)
    return {"registered": True, "duplicate": False}
