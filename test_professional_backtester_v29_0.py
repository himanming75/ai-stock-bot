from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.professional_backtester_v29_0 as m
from backtest.professional_backtester_v29_0 import (
    BacktestBar,
    BacktestError,
    BacktestPolicy,
    load_result,
    run_backtest,
    save_result,
    verify_point,
    verify_result,
    verify_trade,
)

def check(name, condition):
    print(f"{name:<98}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except BacktestError:
        return True
    return False

bars = (
    BacktestBar("2026-01-01","AAPL",Decimal("100"),1,Decimal("0.30"),"a"*64),
    BacktestBar("2026-01-01","MSFT",Decimal("200"),1,Decimal("0.20"),"b"*64),
    BacktestBar("2026-01-02","AAPL",Decimal("105"),1,Decimal("0.30"),"a"*64),
    BacktestBar("2026-01-02","MSFT",Decimal("195"),1,Decimal("0.20"),"b"*64),
    BacktestBar("2026-01-03","AAPL",Decimal("110"),0,Decimal("0.30"),"a"*64),
    BacktestBar("2026-01-03","MSFT",Decimal("190"),-1,Decimal("0.20"),"b"*64),
    BacktestBar("2026-01-04","AAPL",Decimal("108"),-1,Decimal("0.30"),"a"*64),
    BacktestBar("2026-01-04","MSFT",Decimal("185"),-1,Decimal("0.20"),"b"*64),
    BacktestBar("2026-01-05","AAPL",Decimal("104"),-1,Decimal("0.30"),"a"*64),
    BacktestBar("2026-01-05","MSFT",Decimal("180"),0,Decimal("0.20"),"b"*64),
)

policy = BacktestPolicy(
    initial_cash=Decimal("100000"),
    slippage_bps=Decimal("5"),
    commission_per_share=Decimal("0.005"),
    minimum_commission=Decimal("1.00"),
    annualization_factor=252,
)

result = run_backtest(bars, policy)

check("V29.0 engine version verified", m.VERSION == "29.0")
check("Backtest ID created", result.backtest_id.startswith("BT-"))
check("Multi-symbol bars processed", {trade.symbol for trade in result.trades} == {"AAPL","MSFT"})
check("Trade log created", len(result.trades) > 0)
check("Equity curve created", len(result.equity_curve) == 5)
check("Cash tracked", all(point.cash.is_finite() for point in result.equity_curve))
check("Market value tracked", all(point.market_value.is_finite() for point in result.equity_curve))
check("Equity tracked", all(point.equity.is_finite() for point in result.equity_curve))
check("Exposure calculated", all(point.exposure >= Decimal("0") for point in result.equity_curve))
check("Commission applied", any(trade.commission >= Decimal("1.000000") for trade in result.trades))
check("Slippage applied", any(trade.price != next(bar.close for bar in bars if bar.timestamp==trade.timestamp and bar.symbol==trade.symbol) for trade in result.trades))
check("Realized PnL calculated", any(trade.realized_pnl != Decimal("0") for trade in result.trades))
check("Total return calculated", result.metrics.total_return_pct.is_finite())
check("CAGR calculated", result.metrics.cagr_pct.is_finite())
check("Sharpe ratio calculated", result.metrics.sharpe_ratio.is_finite())
check("Maximum drawdown calculated", result.metrics.max_drawdown_pct <= Decimal("0"))
check("Win rate calculated", Decimal("0") <= result.metrics.win_rate <= Decimal("1"))
check("Profit factor calculated", result.metrics.profit_factor >= Decimal("0"))
check("Expectancy calculated", result.metrics.expectancy.is_finite())
check("Exposure ratio calculated", result.metrics.exposure_ratio >= Decimal("0"))
check("Trade hashes verified", all(verify_trade(trade) for trade in result.trades))
check("Equity point hashes verified", all(verify_point(point) for point in result.equity_curve))
check("Backtest result hash verified", verify_result(result))
check("Deterministic backtest returned", result == run_backtest(bars, policy))

fractional = run_backtest(
    bars,
    replace(policy, allow_fractional_shares=True),
)
check("Fractional-share mode completed", fractional.metrics.total_trades > 0)

check("Duplicate bar blocked", blocked(lambda: run_backtest(bars + (bars[0],), policy)))
check("Invalid price blocked", blocked(lambda: run_backtest((replace(bars[0], close=Decimal("0")),), policy)))
check("Invalid signal blocked", blocked(lambda: run_backtest((replace(bars[0], signal=9),), policy)))
check("Invalid target fraction blocked", blocked(lambda: run_backtest((replace(bars[0], target_fraction=Decimal("1.5")),), policy)))
check("Invalid strategy hash blocked", blocked(lambda: run_backtest((replace(bars[0], strategy_hash="BAD"),), policy)))
check("Invalid initial cash blocked", blocked(lambda: BacktestPolicy(initial_cash=0)))

tampered_trade = replace(result.trades[0], price=Decimal("999"))
check("Tampered trade detected", blocked(lambda: verify_trade(tampered_trade)))

tampered_point = replace(result.equity_curve[0], equity=Decimal("1"))
check("Tampered equity point detected", blocked(lambda: verify_point(tampered_point)))

tampered_result = replace(result, result_hash="BROKEN")
check("Tampered backtest result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "backtest.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Backtest save and load passed", loaded == result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["total_trades"] = 999
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved backtest blocked", blocked(lambda: load_result(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {"requests","urllib","httpx","aiohttp","socket","alpaca_trade_api","ib_insync","ccxt"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node,ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node,ast.ImportFrom) and node.module:
        imports.add(node.module.split(".")[0])

check("Forbidden network/broker imports are absent", not(imports & forbidden))
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

print("="*118)
print("V29.0 professional backtesting engine test completed successfully.")
print("Multi-symbol execution, slippage, commission, cash/equity tracking,")
print("CAGR, Sharpe, drawdown, win rate, profit factor, expectancy,")
print("persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
