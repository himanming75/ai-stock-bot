from __future__ import annotations
import os

def inspect()->dict:
    key=bool(os.environ.get("ALPACA_LIVE_API_KEY"))
    secret=bool(os.environ.get("ALPACA_LIVE_SECRET_KEY"))
    return {
        "live_key_present":key,
        "live_secret_present":secret,
        "ready_for_read_only":key and secret,
        "credentials_used":False,
        "credentials_exposed":False,
    }
