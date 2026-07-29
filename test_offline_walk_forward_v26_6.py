from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_walk_forward_v26_6 as m
from backtest.offline_walk_forward_v26_6 import (
    ParameterResult,
    WalkForwardError,
    WalkForwardPolicy,
    create_windows,
    evaluate_fold,
    load_result,
    run_walk_forward,
    save_result,
    verify_fold,
    verify_result,
    verify_window,
)


def check(name, condition):
    print(f"{name:<68}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except WalkForwardError:
        return True
    return False


rolling_policy = WalkForwardPolicy(
    train_size=100,
    test_size=20,
    step_size=20,
    purge_size=5,
    mode="ROLLING",
    min_train_score=Decimal("0.50"),
    min_test_return_pct=Decimal("-2"),
    max_test_drawdown_pct=Decimal("-15"),
    min_efficiency_pct=Decimal("10"),
    max_degradation_pct=Decimal("90"),
)

windows = create_windows(190, rolling_policy)

fold_results = {
    0: (
        ParameterResult("P1", 0.70, 10, -8, 6, -6),
        ParameterResult("P2", 0.60, 8, -5, 5, -4),
    ),
    1: (
        ParameterResult("P1", 0.80, 12, -7, 7, -5),
        ParameterResult("P2", 0.65, 9, -6, 4, -5),
    ),
    2: (
        ParameterResult("P1", 0.75, 11, -9, -4, -18),
        ParameterResult("P2", 0.68, 9, -6, 3, -5),
    ),
    3: (
        ParameterResult("P1", 0.82, 13, -8, 8, -6),
        ParameterResult("P2", 0.70, 10, -6, 6, -5),
    ),
}

result = run_walk_forward(190, fold_results, rolling_policy)

check("V26.6 engine version verified", m.VERSION == "26.6")
check("Rolling windows created", len(windows) == 4)
check("First rolling train window correct", windows[0].train_start == 0 and windows[0].train_end == 100)
check("Purge gap was applied", windows[0].purge_end - windows[0].purge_start == 5)
check("Validation window was created", windows[0].test_start == 105 and windows[0].test_end == 125)
check("Window hash verified", verify_window(windows[0]))
check("Four folds were evaluated", result.total_folds == 4)
check("Best training parameter selected", result.folds[0].selected_parameter_id == "P1")
check("Fold efficiency calculated", result.folds[0].efficiency_pct == Decimal("60.0000"))
check("Failed fold was detected", result.folds[2].passed is False)
check("Failure reasons were recorded", "LOW_TEST_RETURN" in result.folds[2].reason_codes)
check("Passed fold count calculated", result.passed_folds == 3)
check("Failed fold count calculated", result.failed_folds == 1)
check("Pass rate calculated", result.pass_rate_pct == Decimal("75.0000"))
check("Average train return calculated", isinstance(result.average_train_return_pct, Decimal))
check("Average test return calculated", isinstance(result.average_test_return_pct, Decimal))
check("Test stability calculated", result.test_return_stability >= Decimal("0"))
check("Cumulative out-of-sample return calculated", isinstance(result.cumulative_test_return_pct, Decimal))
check("Fold hash verified", verify_fold(result.folds[0]))
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == run_walk_forward(190, fold_results, rolling_policy))

expanding_policy = replace(rolling_policy, mode="EXPANDING")
expanding_windows = create_windows(190, expanding_policy)
check("Expanding windows created", len(expanding_windows) == 4)
check("Expanding train start remains zero", all(window.train_start == 0 for window in expanding_windows))
check("Expanding train end increases", expanding_windows[-1].train_end > expanding_windows[0].train_end)

check("Insufficient data blocked", blocked(lambda: create_windows(100, rolling_policy)))
check("Invalid policy mode blocked", blocked(lambda: WalkForwardPolicy(mode="BAD")))
check("Missing fold results blocked", blocked(lambda: run_walk_forward(
    190,
    {0: fold_results[0]},
    rolling_policy,
)))
check("Unknown fold result blocked", blocked(lambda: run_walk_forward(
    190,
    {**fold_results, 99: fold_results[0]},
    rolling_policy,
)))
check("Duplicate parameter ID blocked", blocked(lambda: evaluate_fold(
    windows[0],
    (
        ParameterResult("P1", 1, 10, -5, 5, -4),
        ParameterResult("P1", 2, 11, -5, 6, -4),
    ),
    rolling_policy,
)))
bad_parameter = ParameterResult("BAD", 1, 10, 5, 5, -4)
check("Positive drawdown blocked", blocked(lambda: evaluate_fold(
    windows[0],
    (bad_parameter,),
    rolling_policy,
)))

tampered_window = replace(windows[0], test_end=999)
check("Tampered window detected", blocked(lambda: verify_window(tampered_window)))

tampered_fold = replace(result.folds[0], test_return_pct=Decimal("999"))
check("Tampered fold detected", blocked(lambda: verify_fold(tampered_fold)))

tampered_result = replace(result, passed_folds=4)
check("Tampered result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "walk_forward.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Result save and load passed", loaded == result)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pass_rate_pct"] = "100.0000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved result blocked", blocked(lambda: load_result(path)))

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

print("=" * 88)
print("V26.6 offline walk-forward validation test completed successfully.")
print("Rolling/expanding windows, purge gaps, parameter selection, out-of-sample")
print("metrics, fold evaluation, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
