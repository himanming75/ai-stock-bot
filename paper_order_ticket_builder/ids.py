from __future__ import annotations
import hashlib
import json

def fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

def client_order_id(
    *,
    plan_id: str,
    symbol: str,
    side: str,
    sequence: int,
) -> str:
    seed = {
        "plan_id": plan_id,
        "symbol": symbol,
        "side": side,
        "sequence": sequence,
    }
    return f"v690-{fingerprint(seed)[:24]}"

def idempotency_key(ticket_payload: dict) -> str:
    return fingerprint(ticket_payload)
