from __future__ import annotations
from datetime import datetime, timezone
import hashlib


def build_live_client_order_id(symbol: str, side: str, seed: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    value = f"l3-{stamp}-{symbol.upper()}-{side}-{digest}"
    return value[:48]
