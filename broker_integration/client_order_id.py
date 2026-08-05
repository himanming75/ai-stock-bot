from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import secrets


def generate_client_order_id(
    symbol: str,
    side: str,
    strategy_id: str,
    nonce: str | None = None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    entropy = nonce or secrets.token_hex(4)
    raw = f"{symbol.upper()}|{side.lower()}|{strategy_id}|{now}|{entropy}"
    suffix = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"p2-{now}-{symbol.upper()}-{side.lower()}-{suffix}"[:48]
