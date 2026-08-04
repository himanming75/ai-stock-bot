from __future__ import annotations
import os

def credentials() -> dict:
    key = os.getenv("ALPACA_PAPER_API_KEY") or os.getenv("APCA_API_KEY_ID") or ""
    secret = os.getenv("ALPACA_PAPER_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or ""
    return {
        "api_key_present": bool(key),
        "secret_key_present": bool(secret),
        "ready": bool(key and secret),
        "key": key,
        "secret": secret,
    }
