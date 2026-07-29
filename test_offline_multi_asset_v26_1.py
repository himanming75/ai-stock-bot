from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_multi_asset_v26_1 as m
from backtest.offline_multi_asset_v26_1 import (
    AssetBar,
    MultiAssetError,
    MultiAssetPolicy,
    load_result,
    run_multi_asset_backtest,
    save_result,
    verify_result,
)


def check(name, condition):
    print(f"{name:<62}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except MultiAssetError:
        return True
    return False


def build_bars():
    series = {
        "AAPL": [100, 101, 102, 103, 104, 105, 106, 107, 108, 106, 104, 102],
        "MSFT": [200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211],
        "NVDA": [50, 49, 48, 47, 46, 45, 44, 43, 42, 43, 44, 45],
    }
    bars = []
    for index in range(12):
        timestamp = f"2026-02-{index + 1:02d}T16:00:00+00:00"
        for symbol, prices in series.items():
            close = Decimal(str(prices[index]))
            bars.append(AssetBar(
                symbol=symbol,
                timestamp=timestamp,
                open=close - Decimal("0.20"),
                high=close + Decimal("1.00"),
                low=close - Decimal("1.00"),
                close=close,
                volume=Decimal("10000"),
            ))
    return bars


policy = MultiAssetPolicy(
    starting_cash=Decimal("100000"),
    max_open_positions=2,
    max_symbol_weight=Decimal("0.30"),
    max_gross_exposure=Decimal("0.60"),
    commission_per_order=Decimal("1"),
    slippage_bps=Decimal("5"),
    fast_period=3,
    slow_period=5,
    min_bars_before_trade=5,
)

bars = build_bars()
result = run_multi_asset_backtest(bars, policy)

check("V26.1 engine version verified", m.VERSION == "26.1")
check("Three symbols were processed", result.symbols == ("AAPL", "MSFT", "NVDA"))
check("Multi-asset result was created", result.ending_equity > Decimal("0"))
check("Portfolio equity curve was created", len(result.equity_curve) == 12)
check("Trades were generated", result.total_trades >= 2)
check("Trade count matches records", result.total_trades == len(result.trades))
check("Per-symbol summaries were created", len(result.symbol_summaries) == 3)
check("Portfolio ended fully in cash", result.equity_curve[-1].gross_exposure == Decimal("0.00"))
check("Ending equity matches final curve", result.ending_equity == result.equity_curve[-1].equity)
check("Maximum drawdown was calculated", result.max_drawdown_pct <= Decimal("0"))
check("Total return was calculated", isinstance(result.total_return_pct, Decimal))
check("AAPL trade activity was recorded", any(t.symbol == "AAPL" for t in result.trades))
check("MSFT trade activity was recorded", any(t.symbol == "MSFT" for t in result.trades))
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == run_multi_asset_backtest(bars, policy))

duplicate = bars + [bars[0]]
check("Duplicate bar was blocked", blocked(lambda: run_multi_asset_backtest(duplicate, policy)))

bad_bar = replace(bars[0], high=Decimal("90"))
check("Invalid OHLC bar was blocked", blocked(lambda: run_multi_asset_backtest([bad_bar] + bars[1:], policy)))

check("Invalid policy was blocked", blocked(lambda: MultiAssetPolicy(
    max_symbol_weight=Decimal("0.80"),
    max_gross_exposure=Decimal("0.50"),
)))

tampered = replace(result, ending_equity=result.ending_equity + Decimal("1"))
check("Tampered result was detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "multi_asset.json"
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

print("=" * 82)
print("V26.1 offline multi-asset engine test completed successfully.")
print("Synchronized multi-symbol replay, independent positions, exposure limits,")
print("trade logs, symbol P&L, equity curve, persistence, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
