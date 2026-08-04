from __future__ import annotations
import os
from typing import Any

PAPER_TRADING_BASE_URL="https://paper-api.alpaca.markets"
MARKET_DATA_BASE_URL="https://data.alpaca.markets"

def credential_status() -> dict[str, Any]:
    key=bool(os.environ.get("ALPACA_PAPER_API_KEY"))
    secret=bool(os.environ.get("ALPACA_PAPER_SECRET_KEY"))
    return {
        "key_present":key,
        "secret_present":secret,
        "complete":key and secret,
        "values_exposed":False,
        "credentials_loaded":False,
        "credentials_used":False,
    }

def headers_from_environment() -> dict[str,str]:
    key=os.environ.get("ALPACA_PAPER_API_KEY","")
    secret=os.environ.get("ALPACA_PAPER_SECRET_KEY","")
    if not key or not secret:
        raise RuntimeError("ALPACA PAPER CREDENTIALS ARE MISSING")
    return {
        "APCA-API-KEY-ID":key,
        "APCA-API-SECRET-KEY":secret,
        "Accept":"application/json",
        "Content-Type":"application/json",
    }
