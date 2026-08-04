from __future__ import annotations
import os


def load() -> dict:
    api_key = os.getenv("ALPACA_PAPER_API_KEY") or os.getenv("APCA_API_KEY_ID") or ""
    secret_key = os.getenv("ALPACA_PAPER_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY") or ""
    return {
        "api_key": api_key,
        "secret_key": secret_key,
        "ready": bool(api_key and secret_key),
    }
