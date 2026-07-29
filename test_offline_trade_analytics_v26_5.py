from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import csv
import json
import tempfile

import backtest.offline_trade_analytics_v26_5 as m
from backtest.offline_trade_analytics_v26_5 import (
    AnalyticsError,
    AnalyticsTrade,
    analyze_trades,
    export_summary_csv,
    filter_trades,
    load_result,
    save_result,
    verify_result,
)


def check(name, condition):
    print(f"{name:<66}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except AnalyticsError:
        return True
    return False


trades = (
    AnalyticsTrade("T1", "AAPL", "LONG", "TREND", "2026-04-01T14:30:00+00:00", "2026-04-02T15:00:00+00:00", "TAKE_PROFIT", 500, 88200, ("trend",)),
    AnalyticsTrade("T2", "MSFT", "LONG", "BREAKOUT", "2026-04-02T14:30:00+00:00", "2026-04-03T16:00:00+00:00", "STOP_LOSS", -250, 91800, ("breakout",)),
    AnalyticsTrade("T3", "AAPL", "SHORT", "REVERSAL", "2026-04-03T14:30:00+00:00", "2026-04-06T17:00:00+00:00", "TARGET", 300, 268200, ("reversal",)),
    AnalyticsTrade("T4", "NVDA", "LONG", "TREND", "2026-04-06T14:30:00+00:00", "2026-04-07T18:00:00+00:00", "TAKE_PROFIT", 1200, 99000, ("trend", "high_conviction")),
    AnalyticsTrade("T5", "MSFT", "SHORT", "REVERSAL", "2026-04-07T14:30:00+00:00", "2026-04-08T19:00:00+00:00", "STOP_LOSS", -600, 102600, ("reversal",)),
    AnalyticsTrade("T6", "AAPL", "LONG", "BREAKOUT", "2026-04-08T14:30:00+00:00", "2026-04-09T20:00:00+00:00", "TIME_EXIT", 0, 106200, ("breakout",)),
)

result = analyze_trades(trades, rolling_window=3)

check("V26.5 engine version verified", m.VERSION == "26.5")
check("Trade classification completed", result.total_trades == 6)
check("Wins counted", result.wins == 3)
check("Losses counted", result.losses == 2)
check("Breakeven counted", result.breakeven == 1)
check("Win rate calculated", result.win_rate_pct == Decimal("50.0000"))
check("Total P&L calculated", result.total_pnl == Decimal("1150.0000"))
check("Average P&L calculated", result.average_pnl == Decimal("191.6667"))
check("Best trade calculated", result.best_trade_pnl == Decimal("1200.0000"))
check("Worst trade calculated", result.worst_trade_pnl == Decimal("-600.0000"))
check("Holding time distribution created", len(result.holding_distribution) >= 1)
check("P&L distribution created", len(result.pnl_distribution) >= 1)
check("LONG statistics created", result.long_stats.trades == 4)
check("SHORT statistics created", result.short_stats.trades == 2)
check("Symbol statistics created", len(result.symbol_stats) == 3)
check("Strategy statistics created", len(result.strategy_stats) == 3)
check("Exit-reason statistics created", len(result.exit_reason_stats) == 4)
check("Weekday statistics created", len(result.weekday_stats) >= 1)
check("Hour statistics created", len(result.hour_stats) >= 1)
check("Rolling performance created", len(result.rolling_performance) == 4)
check("Symbol contribution ranked", result.symbol_contribution[0].key == "NVDA")
check("Consecutive wins/losses calculated", result.max_consecutive_wins >= 1 and result.max_consecutive_losses >= 1)
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == analyze_trades(trades, rolling_window=3))

aapl = filter_trades(trades, symbol="AAPL")
check("Symbol filter passed", len(aapl) == 3 and all(t.symbol == "AAPL" for t in aapl))
reversal = filter_trades(trades, strategy="REVERSAL")
check("Strategy filter passed", len(reversal) == 2)
shorts = filter_trades(trades, direction="SHORT")
check("Direction filter passed", len(shorts) == 2)
date_filtered = filter_trades(
    trades,
    start_time="2026-04-06T00:00:00+00:00",
    end_time="2026-04-09T23:59:59+00:00",
)
check("Date filter passed", len(date_filtered) == 4)

check("Duplicate trade ID blocked", blocked(lambda: analyze_trades(trades + (trades[0],))))
bad_direction = replace(trades[0], direction="SIDEWAYS")
check("Invalid direction blocked", blocked(lambda: analyze_trades((bad_direction,))))
bad_time = replace(trades[0], exit_time=trades[0].entry_time)
check("Invalid exit time blocked", blocked(lambda: analyze_trades((bad_time,))))
check("Invalid rolling window blocked", blocked(lambda: analyze_trades(trades, rolling_window=0)))

tampered = replace(result, total_pnl=Decimal("9999"))
check("Tampered result detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    json_path = folder / "analytics.json"
    csv_path = folder / "analytics.csv"

    save_result(result, json_path)
    loaded = load_result(json_path)
    check("Result save and load passed", loaded == result)

    export_summary_csv(result, csv_path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check("CSV export passed", len(rows) > 0)
    check("CSV contains group types", {"SYMBOL", "STRATEGY"}.issubset({row["group_type"] for row in rows}))

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    payload["total_pnl"] = "9999.0000"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved result blocked", blocked(lambda: load_result(json_path)))

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

print("=" * 86)
print("V26.5 offline trade analytics test completed successfully.")
print("Classification, filtering, distributions, rankings, rolling performance,")
print("JSON persistence, CSV export, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
