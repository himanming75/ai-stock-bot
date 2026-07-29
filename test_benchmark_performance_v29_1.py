from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from datetime import date, timedelta
import ast, json, tempfile

import backtest.benchmark_performance_v29_1 as m
from backtest.benchmark_performance_v29_1 import (
    EquityObservation,
    PerformanceError,
    PerformancePolicy,
    analyze_performance,
    load_report,
    save_report,
    verify_report,
)

def check(name, condition):
    print(f"{name:<100}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except PerformanceError:
        return True
    return False

observations = []
start = date(2025, 12, 15)
strategy = Decimal("100000")
benchmark = Decimal("100000")

for index in range(80):
    day = start + timedelta(days=index)
    # deterministic, non-monotonic paths for both upside and downside periods
    strategy *= Decimal("1.004") if index % 7 not in {3, 4} else Decimal("0.994")
    benchmark *= Decimal("1.0025") if index % 6 not in {2, 3} else Decimal("0.996")
    observations.append(EquityObservation(
        day.isoformat(),
        strategy.quantize(Decimal("0.000001")),
        benchmark.quantize(Decimal("0.000001")),
    ))

policy = PerformancePolicy(
    annualization_factor=252,
    risk_free_rate_pct=Decimal("3"),
    rolling_window=20,
)

report = analyze_performance(observations, policy)

check("V29.1 version verified", m.VERSION == "29.1")
check("Performance report ID created", report.report_id.startswith("PERF-"))
check("All observations retained", len(report.observations) == 80)
check("Strategy total return calculated", report.metrics.strategy_total_return_pct.is_finite())
check("Benchmark total return calculated", report.metrics.benchmark_total_return_pct.is_finite())
check("Excess return calculated", report.metrics.excess_total_return_pct.is_finite())
check("Strategy CAGR calculated", report.metrics.strategy_cagr_pct.is_finite())
check("Benchmark CAGR calculated", report.metrics.benchmark_cagr_pct.is_finite())
check("Annualized volatility calculated", report.metrics.annualized_volatility_pct >= Decimal("0"))
check("Sharpe ratio calculated", report.metrics.sharpe_ratio.is_finite())
check("Sortino ratio calculated", report.metrics.sortino_ratio.is_finite())
check("Maximum drawdown calculated", report.metrics.max_drawdown_pct <= Decimal("0"))
check("Drawdown duration calculated", report.metrics.max_drawdown_duration >= 0)
check("Calmar ratio calculated", report.metrics.calmar_ratio.is_finite())
check("MAR ratio calculated", report.metrics.mar_ratio.is_finite())
check("Alpha calculated", report.metrics.alpha_pct.is_finite())
check("Beta calculated", report.metrics.beta.is_finite())
check("Correlation calculated", Decimal("-1") <= report.metrics.correlation <= Decimal("1"))
check("Tracking error calculated", report.metrics.tracking_error_pct >= Decimal("0"))
check("Information ratio calculated", report.metrics.information_ratio.is_finite())
check("Upside capture calculated", report.metrics.upside_capture_pct.is_finite())
check("Downside capture calculated", report.metrics.downside_capture_pct.is_finite())
check("Monthly returns created", len(report.monthly_returns) >= 3)
check("Yearly returns created", len(report.yearly_returns) == 2)
check("Rolling snapshots created", len(report.rolling_snapshots) == 60)
check("Performance report hash verified", verify_report(report))
check("Deterministic analysis returned", report == analyze_performance(observations, policy))

check("Insufficient observations blocked", blocked(lambda: analyze_performance(observations[:2], policy)))
check("Non-positive strategy equity blocked", blocked(lambda: analyze_performance(
    [replace(observations[0], strategy_equity=Decimal("0"))] + observations[1:], policy
)))
check("Non-positive benchmark equity blocked", blocked(lambda: analyze_performance(
    [replace(observations[0], benchmark_equity=Decimal("0"))] + observations[1:], policy
)))
check("Duplicate timestamp blocked", blocked(lambda: analyze_performance(
    [observations[0], replace(observations[1], timestamp=observations[0].timestamp)] + observations[2:], policy
)))
check("Invalid timestamp blocked", blocked(lambda: analyze_performance(
    [replace(observations[0], timestamp="BAD")] + observations[1:], policy
)))
check("Invalid annualization factor blocked", blocked(lambda: PerformancePolicy(annualization_factor=0)))
check("Invalid rolling window blocked", blocked(lambda: PerformancePolicy(rolling_window=1)))

tampered = replace(report, report_hash="BROKEN")
check("Tampered report detected", blocked(lambda: verify_report(tampered)))

tampered_metric = replace(
    report,
    metrics=replace(report.metrics, max_drawdown_pct=Decimal("1")),
)
check("Invalid drawdown detected", blocked(lambda: verify_report(tampered_metric)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "performance.json"
    save_report(report, path)
    loaded = load_report(path)
    check("Performance report save and load passed", loaded == report)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["alpha_pct"] = "999"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved report blocked", blocked(lambda: load_report(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {"requests","urllib","httpx","aiohttp","socket","alpaca_trade_api","ib_insync","ccxt","yfinance"}
imports=set()
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        imports.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module:
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

print("=" * 120)
print("V29.1 benchmark and advanced performance analysis test completed successfully.")
print("Alpha, beta, correlation, Sortino, Calmar, MAR, tracking error,")
print("information ratio, capture ratios, monthly/yearly returns, rolling analysis,")
print("persistence, hashing, and tamper detection passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
