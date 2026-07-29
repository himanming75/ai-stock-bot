from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_portfolio_optimizer_v26_2 as m
from backtest.offline_portfolio_optimizer_v26_2 import (
    AssetStats,
    OptimizerError,
    OptimizerPolicy,
    load_result,
    optimize_portfolio,
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
    except OptimizerError:
        return True
    return False


stats = (
    AssetStats("AAPL", Decimal("0.14"), Decimal("0.20"), Decimal("0.58"), Decimal("0.08"), Decimal("0.04"), Decimal("0.90")),
    AssetStats("MSFT", Decimal("0.12"), Decimal("0.16"), Decimal("0.56"), Decimal("0.07"), Decimal("0.035"), Decimal("0.95")),
    AssetStats("NVDA", Decimal("0.20"), Decimal("0.35"), Decimal("0.54"), Decimal("0.12"), Decimal("0.06"), Decimal("0.80")),
    AssetStats("JPM", Decimal("0.09"), Decimal("0.14"), Decimal("0.55"), Decimal("0.05"), Decimal("0.03"), Decimal("0.85")),
)

base_policy = OptimizerPolicy(
    cash_reserve_pct=Decimal("0.10"),
    max_symbol_weight=Decimal("0.35"),
    min_symbol_weight=Decimal("0.02"),
    max_assets=4,
    kelly_cap=Decimal("0.25"),
)

equal = optimize_portfolio(stats, replace(base_policy, method="EQUAL"))
inverse = optimize_portfolio(stats, replace(base_policy, method="INVERSE_VOL"))
risk = optimize_portfolio(stats, replace(base_policy, method="RISK_PARITY"))
kelly = optimize_portfolio(stats, replace(base_policy, method="KELLY"))
dynamic = optimize_portfolio(stats, replace(base_policy, method="DYNAMIC"))

check("V26.2 engine version verified", m.VERSION == "26.2")
check("Equal-weight allocation created", equal.method == "EQUAL")
check("Inverse-volatility allocation created", inverse.method == "INVERSE_VOL")
check("Risk-parity allocation created", risk.method == "RISK_PARITY")
check("Kelly allocation created", kelly.method == "KELLY")
check("Dynamic allocation created", dynamic.method == "DYNAMIC")
check("Cash reserve was preserved", dynamic.cash_weight >= Decimal("0.1000"))
check("Invested and cash weights sum to one", dynamic.invested_weight + dynamic.cash_weight == Decimal("1.0000"))
check("Maximum symbol weight respected", all(a.weight <= Decimal("0.3500") for a in dynamic.allocations))
check("Allocations are sorted", tuple(a.symbol for a in dynamic.allocations) == tuple(sorted(a.symbol for a in dynamic.allocations)))
check("Risk contributions were calculated", all(a.risk_contribution >= Decimal("0") for a in dynamic.allocations))
check("Result hash verified", verify_result(dynamic))
check("Deterministic result returned", dynamic == optimize_portfolio(stats, replace(base_policy, method="DYNAMIC")))
check("Inverse volatility favored lower-volatility asset", next(a.weight for a in inverse.allocations if a.symbol == "JPM") >= next(a.weight for a in inverse.allocations if a.symbol == "NVDA"))
check("Kelly produced non-negative weights", all(a.weight >= Decimal("0") for a in kelly.allocations))

limited = optimize_portfolio(stats, replace(base_policy, method="DYNAMIC", max_assets=2))
check("Maximum asset count was enforced", len(limited.allocations) <= 2)

duplicate = stats + (stats[0],)
check("Duplicate symbol was blocked", blocked(lambda: optimize_portfolio(duplicate, base_policy)))
bad_vol = replace(stats[0], volatility=Decimal("0"))
check("Zero volatility was blocked", blocked(lambda: optimize_portfolio((bad_vol,), base_policy)))
check("Invalid method was blocked", blocked(lambda: OptimizerPolicy(method="BAD")))
check("Invalid weight policy was blocked", blocked(lambda: OptimizerPolicy(
    min_symbol_weight=Decimal("0.40"),
    max_symbol_weight=Decimal("0.20"),
)))

tampered = replace(dynamic, cash_weight=Decimal("0.50"))
check("Tampered result was detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "optimizer.json"
    save_result(dynamic, path)
    loaded = load_result(path)
    check("Result save and load passed", loaded == dynamic)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cash_weight"] = "0.5000"
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
print("V26.2 offline portfolio optimizer test completed successfully.")
print("Equal weight, inverse volatility, risk parity, Kelly, dynamic blending,")
print("caps, cash reserve, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
