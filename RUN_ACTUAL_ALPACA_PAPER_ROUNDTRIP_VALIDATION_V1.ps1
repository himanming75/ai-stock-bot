# RUN_ACTUAL_ALPACA_PAPER_ROUNDTRIP_VALIDATION_V1.ps1
# ACTUAL ALPACA PAPER round-trip validation.
# This WILL submit one small PAPER BUY and one PAPER SELL when market is open.
# It never enables E*TRADE/live trading and does not write to strategy performance ledgers.

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

$Root = "C:\stock-bot"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Runtime = Join-Path $Root "runtime\paper_full_auto_validation"

Write-Host "=== ACTUAL ALPACA PAPER ROUNDTRIP VALIDATION V1 ==="

if(-not (Test-Path $Python)) {
    throw "PROJECT VENV PYTHON NOT FOUND"
}

New-Item -ItemType Directory -Path $Runtime -Force | Out-Null

# Explicit hard live locks for the child Python process.
$env:LIVE_TRADING_ENABLED = "false"
$env:ETRADE_LIVE_WRITE_ENABLED = "false"
$env:ETRADE_LIVE_SUBMISSION_ENABLED = "false"

$env:APCA_API_KEY_ID = [Environment]::GetEnvironmentVariable("APCA_API_KEY_ID","User")
$env:APCA_API_SECRET_KEY = [Environment]::GetEnvironmentVariable("APCA_API_SECRET_KEY","User")

if(
    [string]::IsNullOrWhiteSpace($env:APCA_API_KEY_ID) -or
    [string]::IsNullOrWhiteSpace($env:APCA_API_SECRET_KEY)
) {
    throw "ALPACA PAPER CREDENTIALS MISSING"
}

$Code = @'
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\stock-bot")
RUNTIME = ROOT / "runtime" / "paper_full_auto_validation"
LATEST = RUNTIME / "latest_roundtrip_validation.json"
LEDGER = RUNTIME / "roundtrip_validation_ledger.jsonl"

MAX_VALIDATION_NOTIONAL = 10.0
FILL_TIMEOUT_SECONDS = 45
POLL_SECONDS = 2

def now():
    return datetime.now(timezone.utc).isoformat()

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )

def append_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True, default=str) + "\n")

def status(stage, **extra):
    payload = {
        "stage": stage,
        "observed_at_utc": now(),
        "paper_only": True,
        "validation_only": True,
        "strategy_performance_effect": "NONE",
        "etrade_live_write_enabled": False,
        "live_order_submitted": False,
        "maximum_validation_notional": MAX_VALIDATION_NOTIONAL,
    }
    payload.update(extra)
    write_json(LATEST, payload)
    append_jsonl(LEDGER, payload)
    return payload

def wait_order(client, order_id):
    deadline = time.time() + FILL_TIMEOUT_SECONDS
    last = None
    while time.time() < deadline:
        try:
            try:
                last = client.get_order_by_id(order_id)
            except TypeError:
                last = client.get_order_by_id(order_id=order_id)
        except Exception:
            time.sleep(POLL_SECONDS)
            continue
        s = str(getattr(last, "status", "")).lower()
        if "filled" in s:
            return last
        if any(x in s for x in ("canceled", "rejected", "expired")):
            return last
        time.sleep(POLL_SECONDS)
    return last

def main():
    if os.getenv("LIVE_TRADING_ENABLED","").strip().lower() in {"1","true","yes","on","enabled"}:
        return status("BLOCKED", reason="LIVE_TRADING_ENABLED")
    if os.getenv("ETRADE_LIVE_WRITE_ENABLED","").strip().lower() in {"1","true","yes","on","enabled"}:
        return status("BLOCKED", reason="ETRADE_LIVE_WRITE_ENABLED")
    if os.getenv("ETRADE_LIVE_SUBMISSION_ENABLED","").strip().lower() in {"1","true","yes","on","enabled"}:
        return status("BLOCKED", reason="ETRADE_LIVE_SUBMISSION_ENABLED")

    from alpaca.trading.client import TradingClient
    from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
    from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest

    client = TradingClient(
        os.environ["APCA_API_KEY_ID"],
        os.environ["APCA_API_SECRET_KEY"],
        paper=True,
    )

    account = client.get_account()
    if bool(getattr(account, "trading_blocked", False)) or bool(getattr(account, "account_blocked", False)):
        return status("BLOCKED", reason="PAPER_ACCOUNT_BLOCKED")

    clock = client.get_clock()
    if not bool(getattr(clock, "is_open", False)):
        return status(
            "WAITING_FOR_MARKET_OPEN",
            market_open=False,
            next_open=str(getattr(clock, "next_open", "")),
        )

    # Candidate list is intentionally conservative and liquid.
    # Never use a symbol that is already held or has an open order.
    candidate_symbols = ["SPY", "AAPL", "MSFT", "NVDA"]

    positions = list(client.get_all_positions())
    held = {str(getattr(p, "symbol", "")).upper() for p in positions}

    open_orders = client.get_orders(
        filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            limit=500,
        )
    )
    open_order_symbols = {
        str(getattr(o, "symbol", "")).upper()
        for o in open_orders
    }

    symbol = next(
        (
            s for s in candidate_symbols
            if s not in held and s not in open_order_symbols
        ),
        None,
    )

    if not symbol:
        return status(
            "BLOCKED",
            reason="NO_ISOLATED_VALIDATION_SYMBOL_AVAILABLE",
            held_symbols=sorted(held),
            open_order_symbols=sorted(open_order_symbols),
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    buy_cid = f"paper-validation-buy-{stamp}"[:48]

    buy_req = MarketOrderRequest(
        symbol=symbol,
        notional=MAX_VALIDATION_NOTIONAL,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        client_order_id=buy_cid,
    )

    buy = client.submit_order(order_data=buy_req)
    buy_id = str(getattr(buy, "id", ""))

    status(
        "PAPER_VALIDATION_BUY_SUBMITTED",
        symbol=symbol,
        buy_order_id=buy_id,
        buy_client_order_id=buy_cid,
    )

    buy_fill = wait_order(client, buy_id)
    buy_status = str(getattr(buy_fill, "status", "")).lower() if buy_fill else ""
    buy_qty = float(getattr(buy_fill, "filled_qty", 0) or 0) if buy_fill else 0
    buy_price = float(getattr(buy_fill, "filled_avg_price", 0) or 0) if buy_fill else 0

    if "filled" not in buy_status or buy_qty <= 0:
        return status(
            "BLOCKED",
            reason="VALIDATION_BUY_NOT_FILLED",
            symbol=symbol,
            buy_order_id=buy_id,
            buy_status=buy_status,
        )

    sell_cid = f"paper-validation-sell-{stamp}"[:48]
    sell_req = MarketOrderRequest(
        symbol=symbol,
        qty=buy_qty,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
        client_order_id=sell_cid,
    )

    sell = client.submit_order(order_data=sell_req)
    sell_id = str(getattr(sell, "id", ""))

    status(
        "PAPER_VALIDATION_EXIT_SUBMITTED",
        symbol=symbol,
        buy_order_id=buy_id,
        sell_order_id=sell_id,
        quantity=buy_qty,
    )

    sell_fill = wait_order(client, sell_id)
    sell_status = str(getattr(sell_fill, "status", "")).lower() if sell_fill else ""
    sell_qty = float(getattr(sell_fill, "filled_qty", 0) or 0) if sell_fill else 0
    sell_price = float(getattr(sell_fill, "filled_avg_price", 0) or 0) if sell_fill else 0

    if "filled" not in sell_status or sell_qty <= 0:
        return status(
            "BLOCKED",
            reason="VALIDATION_EXIT_NOT_FILLED",
            symbol=symbol,
            buy_order_id=buy_id,
            sell_order_id=sell_id,
            sell_status=sell_status,
        )

    realized_pl = (sell_price - buy_price) * min(buy_qty, sell_qty)

    result = status(
        "ROUNDTRIP_VALIDATION_PASS",
        status="PASS",
        symbol=symbol,
        buy_order_id=buy_id,
        sell_order_id=sell_id,
        buy_price=buy_price,
        sell_price=sell_price,
        buy_quantity=buy_qty,
        sell_quantity=sell_qty,
        realized_pl=round(realized_pl, 8),
        broker_write_performed=True,
        paper_orders_submitted=2,
        closed_roundtrip=True,
    )
    return result

result = main()
print(json.dumps(result, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.get("status") == "PASS" else 3)
'@

$Code | & $Python -
$ExitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=============================================="
Write-Host "VALIDATION SCRIPT EXIT CODE: $ExitCode"
Write-Host "ALPACA PAPER ONLY: ON"
Write-Host "MAX VALIDATION BUY NOTIONAL: $10"
Write-Host "EXISTING POSITIONS TOUCHED: NO"
Write-Host "STRATEGY PERFORMANCE LEDGER TOUCHED: NO"
Write-Host "ETRADE LIVE WRITE: OFF"
Write-Host "=============================================="

exit $ExitCode
