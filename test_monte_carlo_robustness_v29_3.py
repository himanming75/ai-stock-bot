from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.monte_carlo_robustness_v29_3 as m
from backtest.monte_carlo_robustness_v29_3 import (
    MonteCarloError,
    MonteCarloPolicy,
    analyze_monte_carlo,
    load_result,
    save_result,
    verify_path,
    verify_result,
)

def check(name, condition):
    print(f"{name:<104}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except MonteCarloError:
        return True
    return False

returns = []
for index in range(120):
    cycle = index % 10
    if cycle in {3, 8}:
        returns.append(Decimal("-0.006"))
    elif cycle == 6:
        returns.append(Decimal("-0.003"))
    else:
        returns.append(Decimal("0.004"))

policy = MonteCarloPolicy(
    simulations=500,
    seed=2903,
    mode="bootstrap",
    ruin_threshold_pct=Decimal("-35"),
    confidence_level=Decimal("0.95"),
    minimum_robustness_score=Decimal("55"),
)

result = analyze_monte_carlo(returns, policy)

check("V29.3 version verified", m.VERSION == "29.3")
check("Analysis ID created", result.analysis_id.startswith("MCR-"))
check("Source return count retained", result.source_return_count == len(returns))
check("Requested simulation count created", len(result.paths) == 500)
check("Simulation IDs are unique", len({path.simulation_id for path in result.paths}) == 500)
check("Terminal returns calculated", all(path.terminal_return_pct.is_finite() for path in result.paths))
check("Maximum drawdowns calculated", all(path.max_drawdown_pct <= Decimal("0") for path in result.paths))
check("Ruin flags calculated", all(isinstance(path.ruined, bool) for path in result.paths))
check("Mean terminal return calculated", result.metrics.mean_terminal_return_pct.is_finite())
check("Median terminal return calculated", result.metrics.median_terminal_return_pct.is_finite())
check("Return percentiles ordered",
      result.metrics.worst_terminal_return_pct
      <= result.metrics.percentile_5_return_pct
      <= result.metrics.percentile_25_return_pct
      <= result.metrics.median_terminal_return_pct
      <= result.metrics.percentile_75_return_pct
      <= result.metrics.percentile_95_return_pct
      <= result.metrics.best_terminal_return_pct)
check("Mean drawdown calculated", result.metrics.mean_max_drawdown_pct <= Decimal("0"))
check("Worst drawdown calculated", result.metrics.worst_max_drawdown_pct <= result.metrics.mean_max_drawdown_pct)
check("Loss probability calculated", Decimal("0") <= result.metrics.loss_probability <= Decimal("1"))
check("Ruin probability calculated", Decimal("0") <= result.metrics.ruin_probability <= Decimal("1"))
check("Value at Risk calculated", result.metrics.value_at_risk_pct.is_finite())
check("Conditional Value at Risk calculated", result.metrics.conditional_value_at_risk_pct <= result.metrics.value_at_risk_pct)
check("Robustness score calculated", Decimal("0") <= result.metrics.robustness_score <= Decimal("100"))
check("Validation decision calculated", isinstance(result.metrics.validation_passed, bool))
check("Path hashes verified", all(verify_path(path) for path in result.paths))
check("Result hash verified", verify_result(result))
check("Deterministic bootstrap analysis returned", result == analyze_monte_carlo(returns, policy))

shuffle_result = analyze_monte_carlo(
    returns,
    replace(policy, mode="shuffle", simulations=200),
)
check("Shuffle mode completed", shuffle_result.metrics.simulation_count == 200)
check("Shuffle terminal returns remain equal",
      len({path.terminal_return_pct for path in shuffle_result.paths}) == 1)
check("Shuffle drawdown sequence varies",
      len({path.max_drawdown_pct for path in shuffle_result.paths}) > 1)

check("Insufficient returns blocked", blocked(lambda: analyze_monte_carlo(returns[:9], policy)))
check("Return below minus 100 percent blocked",
      blocked(lambda: analyze_monte_carlo([Decimal("-1")] + returns[1:], policy)))
check("Too few simulations blocked", blocked(lambda: MonteCarloPolicy(simulations=99)))
check("Invalid mode blocked", blocked(lambda: MonteCarloPolicy(mode="invalid")))
check("Non-negative ruin threshold blocked",
      blocked(lambda: MonteCarloPolicy(ruin_threshold_pct=Decimal("0"))))
check("Invalid confidence level blocked",
      blocked(lambda: MonteCarloPolicy(confidence_level=Decimal("1"))))
check("Invalid minimum robustness score blocked",
      blocked(lambda: MonteCarloPolicy(minimum_robustness_score=Decimal("101"))))

tampered_path = replace(result.paths[0], terminal_return_pct=Decimal("999"))
check("Tampered path detected", blocked(lambda: verify_path(tampered_path)))

tampered_result = replace(result, result_hash="BROKEN")
check("Tampered result detected", blocked(lambda: verify_result(tampered_result)))

tampered_probability = replace(
    result,
    metrics=replace(result.metrics, ruin_probability=Decimal("2")),
)
check("Invalid probability detected", blocked(lambda: verify_result(tampered_probability)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "monte_carlo.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Monte Carlo result save and load passed", loaded == result)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["robustness_score"] = "999"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved result blocked", blocked(lambda: load_result(path)))

tree = ast.parse(Path(m.__file__).read_text(encoding="utf-8"))
forbidden = {
    "requests", "urllib", "httpx", "aiohttp", "socket",
    "alpaca_trade_api", "ib_insync", "ccxt", "yfinance"
}
imports = set()

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

print("=" * 124)
print("V29.3 Monte Carlo and robustness analysis test completed successfully.")
print("Bootstrap/shuffle simulations, terminal-return distribution, drawdown distribution,")
print("loss and ruin probabilities, VaR, CVaR, robustness scoring, persistence,")
print("hashing, and tamper detection passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
