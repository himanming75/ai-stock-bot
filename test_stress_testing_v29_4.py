from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.stress_testing_v29_4 as m
from backtest.stress_testing_v29_4 import (
    StressPolicy,
    StressScenario,
    StressTestError,
    default_scenarios,
    load_result,
    run_stress_test,
    save_result,
    verify_result,
    verify_scenario_result,
)

def check(name, condition):
    print(f"{name:<106}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except StressTestError:
        return True
    return False

returns = []
for index in range(120):
    cycle = index % 10
    if cycle in {3, 8}:
        returns.append(Decimal("-0.005"))
    elif cycle == 6:
        returns.append(Decimal("-0.002"))
    else:
        returns.append(Decimal("0.004"))

policy = StressPolicy(
    survival_equity_floor_pct=Decimal("45"),
    maximum_acceptable_drawdown_pct=Decimal("-45"),
    minimum_stress_score=Decimal("50"),
    recovery_horizon=20,
)

result = run_stress_test(returns, policy=policy)

check("V29.4 version verified", m.VERSION == "29.4")
check("Stress analysis ID created", result.analysis_id.startswith("STR-"))
check("Default scenarios loaded", len(result.scenarios) == 7)
check("All scenario names are unique", len({x.name for x in result.scenarios}) == 7)
check("Scenario results created", len(result.scenario_results) == 7)
check("Flash crash scenario included", any(x.scenario_name == "FLASH_CRASH" for x in result.scenario_results))
check("Bear market scenario included", any(x.scenario_name == "PROLONGED_BEAR_MARKET" for x in result.scenario_results))
check("Volatility spike scenario included", any(x.scenario_name == "VOLATILITY_SPIKE" for x in result.scenario_results))
check("Sideways scenario included", any(x.scenario_name == "SIDEWAYS_MARKET" for x in result.scenario_results))
check("Consecutive-loss scenario included", any(x.scenario_name == "CONSECUTIVE_LOSSES" for x in result.scenario_results))
check("Liquidity shock scenario included", any(x.scenario_name == "LIQUIDITY_SHOCK" for x in result.scenario_results))
check("Commission shock scenario included", any(x.scenario_name == "COMMISSION_SHOCK" for x in result.scenario_results))
check("Terminal returns calculated", all(x.terminal_return_pct.is_finite() for x in result.scenario_results))
check("Maximum drawdowns calculated", all(x.max_drawdown_pct <= Decimal("0") for x in result.scenario_results))
check("Minimum equity calculated", all(x.minimum_equity_pct > Decimal("0") for x in result.scenario_results))
check("Recovery periods calculated", all(x.recovery_periods >= 0 for x in result.scenario_results))
check("Survival decisions calculated", all(isinstance(x.survived, bool) for x in result.scenario_results))
check("Resilience scores calculated", all(Decimal("0") <= x.resilience_score <= Decimal("100") for x in result.scenario_results))
check("Scenario hashes verified", all(verify_scenario_result(x) for x in result.scenario_results))
check("Scenario count metric calculated", result.metrics.scenario_count == 7)
check("Survival ratio calculated", Decimal("0") <= result.metrics.survival_ratio <= Decimal("1"))
check("Average terminal return calculated", result.metrics.average_terminal_return_pct.is_finite())
check("Worst terminal return calculated", result.metrics.worst_terminal_return_pct <= result.metrics.average_terminal_return_pct)
check("Average drawdown calculated", result.metrics.average_max_drawdown_pct <= Decimal("0"))
check("Worst drawdown calculated", result.metrics.worst_max_drawdown_pct <= result.metrics.average_max_drawdown_pct)
check("Average resilience calculated", Decimal("0") <= result.metrics.average_resilience_score <= Decimal("100"))
check("Stress score calculated", Decimal("0") <= result.metrics.stress_score <= Decimal("100"))
check("Validation decision calculated", isinstance(result.metrics.validation_passed, bool))
check("Stress result hash verified", verify_result(result))
check("Deterministic stress test returned", result == run_stress_test(returns, policy=policy))

custom_scenarios = (
    StressScenario(
        name="CUSTOM_GAP_DOWN",
        shock_index=5,
        shock_return=Decimal("-0.15"),
        severity_weight=Decimal("1.3"),
    ),
    StressScenario(
        name="CUSTOM_COST_SHOCK",
        cost_drag_per_period=Decimal("-0.002"),
        severity_weight=Decimal("1.0"),
    ),
)
custom = run_stress_test(returns, custom_scenarios, policy)
check("Custom scenarios completed", custom.metrics.scenario_count == 2)

check("Insufficient returns blocked", blocked(lambda: run_stress_test(returns[:19], policy=policy)))
check("Invalid base return blocked", blocked(lambda: run_stress_test([Decimal("-1")] + returns[1:], policy=policy)))
check("Empty scenarios blocked", blocked(lambda: run_stress_test(returns, (), policy)))
check("Duplicate scenario names blocked", blocked(lambda: run_stress_test(
    returns, (custom_scenarios[0], custom_scenarios[0]), policy
)))
check("Out-of-range shock index blocked", blocked(lambda: run_stress_test(
    returns,
    (StressScenario(name="BAD_INDEX", shock_index=999, shock_return=Decimal("-0.1")),),
    policy,
)))
check("Invalid survival floor blocked", blocked(lambda: StressPolicy(survival_equity_floor_pct=Decimal("100"))))
check("Invalid acceptable drawdown blocked", blocked(lambda: StressPolicy(maximum_acceptable_drawdown_pct=Decimal("0"))))
check("Invalid minimum stress score blocked", blocked(lambda: StressPolicy(minimum_stress_score=Decimal("101"))))
check("Invalid recovery horizon blocked", blocked(lambda: StressPolicy(recovery_horizon=0)))
check("Invalid scenario name blocked", blocked(lambda: StressScenario(name="")))
check("Invalid scenario multiplier blocked", blocked(lambda: StressScenario(name="BAD", return_multiplier=Decimal("-1"))))
check("Invalid shock return blocked", blocked(lambda: StressScenario(name="BAD", shock_return=Decimal("-1"))))
check("Invalid loss count blocked", blocked(lambda: StressScenario(name="BAD", consecutive_loss_count=-1)))
check("Invalid severity weight blocked", blocked(lambda: StressScenario(name="BAD", severity_weight=Decimal("0"))))

tampered_scenario = replace(result.scenario_results[0], terminal_return_pct=Decimal("999"))
check("Tampered scenario result detected", blocked(lambda: verify_scenario_result(tampered_scenario)))

tampered_result = replace(result, result_hash="BROKEN")
check("Tampered stress result detected", blocked(lambda: verify_result(tampered_result)))

invalid_score = replace(
    result,
    metrics=replace(result.metrics, stress_score=Decimal("999")),
)
check("Invalid stress score detected", blocked(lambda: verify_result(invalid_score)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "stress_test.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Stress result save and load passed", loaded == result)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["survival_ratio"] = "2"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved stress result blocked", blocked(lambda: load_result(path)))

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

print("=" * 126)
print("V29.4 stress testing engine test completed successfully.")
print("Flash crash, bear market, volatility spike, sideways market,")
print("consecutive losses, liquidity and commission shocks, custom scenarios,")
print("survival, recovery, resilience, persistence, hashing, and tamper detection passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
