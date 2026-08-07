from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()

def out(obj):
    print(json.dumps(obj, indent=2, default=str), flush=True)

def env(name):
    return os.getenv(name, "").strip()

def load_client():
    from alpaca.trading.client import TradingClient
    key = env("APCA_API_KEY_ID")
    secret = env("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise RuntimeError("ALPACA_PAPER_CREDENTIALS_MISSING")
    return TradingClient(key, secret, paper=True)

def open_orders(client):
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest
    return list(client.get_orders(
        filter=GetOrdersRequest(status=QueryOrderStatus.OPEN, limit=500)
    ))

def position_rows(client):
    rows = []
    for p in client.get_all_positions():
        rows.append({
            "symbol": str(getattr(p, "symbol", "")).upper(),
            "qty": str(getattr(p, "qty", "")),
        })
    return rows

def order_rows(orders):
    rows = []
    for o in orders:
        rows.append({
            "id": str(getattr(o, "id", "")),
            "symbol": str(getattr(o, "symbol", "")).upper(),
            "side": str(getattr(o, "side", "")),
            "status": str(getattr(o, "status", "")),
            "created_at": str(getattr(o, "created_at", "")),
        })
    return rows

def has_open_sell(orders, symbol):
    symbol = symbol.upper()
    for o in orders:
        if str(getattr(o, "symbol", "")).upper() != symbol:
            continue
        if "sell" in str(getattr(o, "side", "")).lower():
            return True
    return False

def maybe_submit_missing_close_orders(client):
    """
    Never duplicates an existing open SELL for the same symbol.
    Called only while the market is open.
    """
    orders = open_orders(client)
    submitted = []
    for p in client.get_all_positions():
        symbol = str(getattr(p, "symbol", "")).upper()
        if not symbol:
            continue
        if has_open_sell(orders, symbol):
            continue
        order = client.close_position(symbol)
        submitted.append({
            "symbol": symbol,
            "order_id": str(getattr(order, "id", "")),
        })
        orders = open_orders(client)
    return submitted

def status(client):
    clock = client.get_clock()
    positions = position_rows(client)
    orders = open_orders(client)
    return {
        "paper_only": True,
        "market_open": bool(getattr(clock, "is_open", False)),
        "timestamp": str(getattr(clock, "timestamp", "")),
        "next_open": str(getattr(clock, "next_open", "")),
        "next_close": str(getattr(clock, "next_close", "")),
        "positions": positions,
        "position_count": len(positions),
        "open_orders": order_rows(orders),
        "open_order_count": len(orders),
    }

def wait_until_flat(client, timeout_seconds=900):
    start = time.time()
    submitted = []
    while time.time() - start <= timeout_seconds:
        s = status(client)
        if s["position_count"] == 0 and s["open_order_count"] == 0:
            s["status"] = "FLAT"
            s["new_close_orders_submitted"] = submitted
            return s

        if not s["market_open"]:
            s["status"] = "WAITING_FOR_MARKET_OPEN"
            s["new_close_orders_submitted"] = submitted
            return s

        # If a position exists but no matching open SELL exists, submit exactly one close.
        new_orders = maybe_submit_missing_close_orders(client)
        submitted.extend(new_orders)

        time.sleep(2)

    s = status(client)
    s["status"] = "FLATTEN_TIMEOUT"
    s["new_close_orders_submitted"] = submitted
    return s

if __name__ == "__main__":
    client = load_client()
    result = wait_until_flat(client)
    out(result)
    if result["status"] == "FLAT":
        raise SystemExit(0)
    if result["status"] == "WAITING_FOR_MARKET_OPEN":
        raise SystemExit(10)
    raise SystemExit(4)
