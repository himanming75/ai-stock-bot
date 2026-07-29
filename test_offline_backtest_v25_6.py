from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.offline_backtest_v25_6 as m
from backtest.offline_backtest_v25_6 import (
    BacktestError, BacktestPolicy, Bar, load_result,
    run_backtest, save_result, verify_result,
)


def check(name, condition):
    print(f"{name:<60}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except BacktestError:
        return True
    return False


def make_bars():
    prices = [
        100, 100.5, 101, 101.5, 102, 102.5, 103, 103.5, 104, 104.5,
        105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
        112, 110, 108, 106, 104, 103, 104, 105, 106, 107,
        108, 109, 110, 111, 112, 113, 114, 115, 116, 117,
    ]
    bars = []
    for i, close in enumerate(prices):
        open_price = Decimal(str(close)) - Decimal("0.2")
        high = Decimal(str(close)) + Decimal("1.0")
        low = Decimal(str(close)) - Decimal("1.0")
        bars.append(Bar(
            f"2026-01-{i+1:02d}T16:00:00+00:00",
            open_price, high, low, close, 10000,
        ))
    return bars


policy = BacktestPolicy(
    starting_cash=Decimal("100000"),
    fast_ema_period=3,
    slow_ema_period=6,
    rsi_period=4,
    atr_period=4,
    breakout_lookback=4,
    risk_per_trade_pct=Decimal("0.01"),
    max_position_pct=Decimal("0.25"),
    atr_stop_multiple=Decimal("2"),
    take_profit_r_multiple=Decimal("2"),
    commission_per_order=Decimal("1"),
    slippage_bps=Decimal("5"),
    min_bars_before_trade=6,
)

bars = make_bars()
result = run_backtest("AAPL", bars, policy)

check("V25.6 engine version verified", m.VERSION == "25.6")
check("Backtest result was created", result.symbol == "AAPL")
check("All bars were replayed", len(result.equity_curve) == len(bars))
check("At least one trade was generated", result.total_trades >= 1)
check("Trade count matches records", result.total_trades == len(result.trades))
check("Ending equity was calculated", result.ending_equity > Decimal("0"))
check("Total return was calculated", isinstance(result.total_return_pct, Decimal))
check("Maximum drawdown was calculated", result.max_drawdown_pct <= Decimal("0"))
check("Win rate is bounded", Decimal("0") <= result.win_rate <= Decimal("100"))
check("Profit factor was calculated", result.profit_factor >= Decimal("0"))
check("Sharpe ratio was calculated", isinstance(result.sharpe_ratio, Decimal))
check("Equity curve ends at ending equity", result.equity_curve[-1].equity == result.ending_equity)
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == run_backtest("AAPL", bars, policy))
check("Trade P&L was calculated", all(isinstance(t.net_pnl, Decimal) for t in result.trades))
check("Exit reasons were recorded", all(t.exit_reason for t in result.trades))

check("Insufficient bars were blocked", blocked(lambda: run_backtest("AAPL", bars[:5], policy)))
bad_bar = replace(bars[0], high=Decimal("90"))
check("Invalid OHLC bar was blocked", blocked(lambda: run_backtest("AAPL", [bad_bar] + bars[1:], policy)))
bad_times = list(bars)
bad_times[2] = replace(bad_times[2], timestamp=bad_times[1].timestamp)
check("Duplicate timestamp was blocked", blocked(lambda: run_backtest("AAPL", bad_times, policy)))
check("Invalid policy was blocked", blocked(lambda: BacktestPolicy(fast_ema_period=10, slow_ema_period=5)))

tampered = replace(result, ending_equity=result.ending_equity + Decimal("1"))
check("Tampered result was detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "backtest.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Result save and load passed", loaded == result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["ending_equity"] = "999999.00"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved result was blocked", blocked(lambda: load_result(path)))

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

print("=" * 80)
print("V25.6 offline backtest engine test completed successfully.")
print("OHLCV replay, indicators, signals, risk sizing, fills, portfolio updates,")
print("trade logs, equity curve, metrics, persistence, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
