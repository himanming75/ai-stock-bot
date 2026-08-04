from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from real_paper_micro_order.io import load_json, write_json

def path(root: Path) -> Path:
    return root / "release/v306_01_to_v310_64/control/one_time_micro_order_token.json"

def inspect(root: Path, phrase: str) -> dict:
    value = load_json(path(root))
    valid = (
        value.get("enabled") is True
        and value.get("consumed") is not True
        and value.get("phrase") == phrase
    )
    return {"valid": valid, "value": value}

def consume(root: Path, client_order_id: str) -> dict:
    value = load_json(path(root))
    value.update({
        "enabled": False,
        "consumed": True,
        "client_order_id": client_order_id,
        "consumed_at": datetime.now(timezone.utc).isoformat(),
    })
    write_json(path(root), value)
    return value
