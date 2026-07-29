from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_performance_v26_3 as m
from backtest.offline_performance_v26_3 import (
    EquitySample,
    PerformanceError,
    TradeSample,
    analyze_performance,
    load_result,
    save_result,
    verify_result,
)


def check(name, condition):
    print(f"{name:<64}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except PerformanceError:
        return True
    return False


equity = (
    EquitySample("2025-01-01T16:00:00+00:00", 100000),
    EquitySample("2025-02-01T16:00:00+00:00", 103000),
    EquitySample("2025-03-01T16:00:00+00:00", 101000),
    EquitySample("2025-04-01T16:00:00+00:00", 106000),
    EquitySample("2025-05-01T16:00:00+00:00", 109000),
    EquitySample("2025-06-01T16:00:00+00:00", 108000),
    EquitySample("2025-07-01T16:00:00+00:00", 112000),
    EquitySample("2025-08-01T16:00:00+00:00", 115000),
    EquitySample("2025-09-01T16:00:00+00:00", 113000),
    EquitySample("2025-10-01T16:00:00+00:00", 118000),
    EquitySample("2025-11-01T16:00:00+00:00", 121000),
    EquitySample("2025-12-01T16:00:00+00:00", 125000),
    EquitySample("2026-01-01T16:00:00+00:00", 130000),
)

trades = (
    TradeSample(2.0, 2000, 5),
    TradeSample(-1.0, -1000, 3),
    TradeSample(3.0, 3000, 7),
    TradeSample(1.5, 1500, 4),
    TradeSample(-0.5, -500, 2),
    TradeSample(2.5, 2500, 6),
)

benchmark = [0.02, -0.01, 0.03, 0.02, -0.005, 0.025, 0.02, -0.01, 0.03, 0.02, 0.025, 0.03]

result = analyze_performance(
    equity,
    trades,
    benchmark,
    periods_per_year=12,
    risk_free_rate_pct=2,
)

check("V26.3 engine version verified", m.VERSION == "26.3")
check("Total return was calculated", result.total_return_pct == Decimal("30.0000"))
check("CAGR was calculated", result.cagr_pct > Decimal("0"))
check("Annual return was calculated", isinstance(result.annual_return_pct, Decimal))
check("Annual volatility was calculated", result.annual_volatility_pct >= Decimal("0"))
check("Sharpe ratio was calculated", isinstance(result.sharpe_ratio, Decimal))
check("Sortino ratio was calculated", isinstance(result.sortino_ratio, Decimal))
check("Maximum drawdown was calculated", result.max_drawdown_pct <= Decimal("0"))
check("Calmar ratio was calculated", isinstance(result.calmar_ratio, Decimal))
check("MAR ratio was calculated", result.mar_ratio == result.calmar_ratio)
check("Win rate was calculated", result.win_rate_pct == Decimal("66.6667"))
check("Profit factor was calculated", result.profit_factor > Decimal("1"))
check("Expectancy was calculated", result.expectancy > Decimal("0"))
check("Average win and loss were calculated", result.average_win > Decimal("0") and result.average_loss > Decimal("0"))
check("Payoff ratio was calculated", result.payoff_ratio > Decimal("0"))
check("Holding period was calculated", result.average_holding_period > Decimal("0"))
check("Consecutive streaks were calculated", result.max_consecutive_wins >= 1 and result.max_consecutive_losses >= 1)
check("Recovery factor was calculated", isinstance(result.recovery_factor, Decimal))
check("SQN was calculated", isinstance(result.sqn, Decimal))
check("Alpha and beta were calculated", isinstance(result.alpha_pct, Decimal) and isinstance(result.beta, Decimal))
check("Information ratio was calculated", isinstance(result.information_ratio, Decimal))
check("Monthly returns were created", len(result.monthly_returns) == 13)
check("Yearly returns were created", len(result.yearly_returns) == 2)
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == analyze_performance(equity, trades, benchmark, periods_per_year=12, risk_free_rate_pct=2))

check("Insufficient equity blocked", blocked(lambda: analyze_performance(equity[:1], trades)))
duplicate_equity = equity + (equity[0],)
check("Duplicate timestamp blocked", blocked(lambda: analyze_performance(duplicate_equity, trades)))
bad_equity = replace(equity[0], equity=Decimal("0"))
check("Invalid equity blocked", blocked(lambda: analyze_performance((bad_equity,) + equity[1:], trades)))
check("Benchmark length mismatch blocked", blocked(lambda: analyze_performance(equity, trades, benchmark[:3], periods_per_year=12)))

tampered = replace(result, win_rate_pct=Decimal("99"))
check("Tampered result was detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "performance.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Result save and load passed", loaded == result)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["total_return_pct"] = "999.0000"
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

print("=" * 84)
print("V26.3 offline performance analyzer test completed successfully.")
print("CAGR, volatility, Sharpe, Sortino, Calmar, MAR, trade statistics,")
print("alpha, beta, information ratio, persistence, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
