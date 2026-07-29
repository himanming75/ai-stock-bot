from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import csv
import json
import tempfile

import backtest.offline_trade_journal_v26_4 as m
from backtest.offline_trade_journal_v26_4 import (
    JournalError,
    close_trade,
    create_journal,
    create_trade,
    export_csv,
    load_journal,
    save_journal,
    verify_journal,
    verify_record,
)


def check(name, condition):
    print(f"{name:<64}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except JournalError:
        return True
    return False


long_open = create_trade(
    "AAPL",
    "LONG",
    "2026-03-01T14:30:00+00:00",
    100,
    10,
    signal_reason="TREND_BREAKOUT",
    signal_snapshot={"action": "BUY", "confidence": "0.82"},
    indicator_snapshot={"rsi": "61.2", "ema_fast": "101.0", "ema_slow": "98.5"},
    portfolio_snapshot={"cash": "90000", "equity": "100000"},
    entry_commission=1,
    entry_slippage=0.50,
    tags=("breakout", "trend"),
)
long_closed = close_trade(
    long_open,
    "2026-03-05T20:00:00+00:00",
    110,
    exit_reason="TAKE_PROFIT",
    exit_commission=1,
    exit_slippage=0.50,
)

short_open = create_trade(
    "MSFT",
    "SHORT",
    "2026-03-02T14:30:00+00:00",
    200,
    5,
    signal_reason="BEARISH_REVERSAL",
    signal_snapshot={"action": "SELL", "confidence": "0.78"},
    indicator_snapshot={"rsi": "72.0"},
    portfolio_snapshot={"cash": "95000"},
    entry_commission=1,
    entry_slippage=0.25,
    tags=("reversal",),
)
short_closed = close_trade(
    short_open,
    "2026-03-04T20:00:00+00:00",
    190,
    exit_reason="TARGET_REACHED",
    exit_commission=1,
    exit_slippage=0.25,
)

journal = create_journal((long_closed, short_closed))

check("V26.4 engine version verified", m.VERSION == "26.4")
check("Trade ID was generated", long_open.entry.trade_id.startswith("TRD-"))
check("LONG direction stored", long_open.entry.direction == "LONG")
check("SHORT direction stored", short_open.entry.direction == "SHORT")
check("Signal snapshot stored", dict(long_open.entry.signal_snapshot)["action"] == "BUY")
check("Indicator snapshot stored", dict(long_open.entry.indicator_snapshot)["rsi"] == "61.2")
check("Portfolio snapshot stored", dict(long_open.entry.portfolio_snapshot)["equity"] == "100000")
check("Entry commission stored", long_open.entry.entry_commission == Decimal("1.00"))
check("Entry slippage stored", long_open.entry.entry_slippage == Decimal("0.50"))
check("Holding time calculated", long_closed.holding_seconds > 0)
check("LONG gross P&L calculated", long_closed.gross_pnl == Decimal("100.00"))
check("LONG net P&L calculated", long_closed.net_pnl == Decimal("97.00"))
check("SHORT gross P&L calculated", short_closed.gross_pnl == Decimal("50.00"))
check("SHORT net P&L calculated", short_closed.net_pnl == Decimal("47.50"))
check("Tags stored and sorted", long_open.entry.tags == ("breakout", "trend"))
check("Trade record hash verified", verify_record(long_closed))
check("Journal hash verified", verify_journal(journal))
check("Deterministic trade ID returned", long_open.entry.trade_id == create_trade(
    "AAPL", "LONG", "2026-03-01T14:30:00+00:00", 100, 10,
    signal_reason="TREND_BREAKOUT",
).entry.trade_id)

check("Duplicate trade ID blocked", blocked(lambda: create_journal((long_closed, long_closed))))
check("Invalid direction blocked", blocked(lambda: create_trade(
    "AAPL", "SIDEWAYS", "2026-03-01T14:30:00+00:00", 100, 10,
    signal_reason="TEST",
)))
check("Invalid quantity blocked", blocked(lambda: create_trade(
    "AAPL", "LONG", "2026-03-01T14:30:00+00:00", 100, 0,
    signal_reason="TEST",
)))
check("Invalid price blocked", blocked(lambda: create_trade(
    "AAPL", "LONG", "2026-03-01T14:30:00+00:00", 0, 10,
    signal_reason="TEST",
)))
check("Invalid exit time blocked", blocked(lambda: close_trade(
    long_open,
    "2026-03-01T14:00:00+00:00",
    110,
    exit_reason="BAD_TIME",
)))
check("Double close blocked", blocked(lambda: close_trade(
    long_closed,
    "2026-03-06T20:00:00+00:00",
    111,
    exit_reason="SECOND_CLOSE",
)))

tampered_record = replace(long_closed, net_pnl=Decimal("999.00"))
check("Tampered record detected", blocked(lambda: verify_record(tampered_record)))

tampered_journal = replace(journal, journal_hash="BROKEN")
check("Tampered journal detected", blocked(lambda: verify_journal(tampered_journal)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    json_path = folder / "journal.json"
    csv_path = folder / "journal.csv"

    save_journal(journal, json_path)
    loaded = load_journal(json_path)
    check("Journal save and load passed", loaded == journal)

    export_csv(journal, csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check("CSV export passed", len(rows) == 2)
    check("CSV includes trade IDs", all(row["trade_id"] for row in rows))

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["trades"][0]["net_pnl"] = "999.00"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved journal blocked", blocked(lambda: load_journal(json_path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt",
}
imports = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not (imports & forbidden))
check("Market data API was not called", not m.MARKET_DATA_API_CALLED)
check("Account API was not called", not m.ACCOUNT_API_CALLED)
check("Network was not accessed", not m.NETWORK_ACCESSED)
check("Broker API was not called", not m.BROKER_API_CALLED)
check("Broker order was not created", not m.BROKER_ORDER_CREATED)
check("Order was not submitted", not m.ORDER_SUBMITTED)
check("Live execution not authorized", not m.LIVE_EXECUTION_AUTHORIZED)
check("Funds were not reserved", not m.FUNDS_RESERVED)
check("Holdings were not reserved", not m.HOLDINGS_RESERVED)
check("All checks passed", True)

print("=" * 84)
print("V26.4 offline trade journal test completed successfully.")
print("Trade IDs, entries, exits, snapshots, costs, P&L, holding time, tags,")
print("JSON persistence, CSV export, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
