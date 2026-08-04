from __future__ import annotations
import hashlib
from datetime import datetime, timezone

def client_order_id(strategy_id: str, symbol: str, side: str, nonce: str) -> str:
    raw = f"{strategy_id}|{symbol.upper()}|{side.upper()}|{nonce}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return f"AISB-{digest}"

def mapping(client_id: str, broker_id: str | None = None) -> dict:
    return {
        "client_order_id": client_id,
        "broker_order_id": broker_id,
        "mapped_at": datetime.now(timezone.utc).isoformat(),
    }
