from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast, json, tempfile

import backtest.walk_forward_validation_v29_2 as m
from backtest.walk_forward_validation_v29_2 import (
    ReturnObservation,
    WalkForwardError,
    WalkForwardPolicy,
    load_result,
    run_walk_forward_validation,
    save_result,
    verify_result,
    verify_window,
)

def check(name, condition):
    print(f"{name:<102}: {condition}")
    if not condition:
        raise AssertionError(name)

def blocked(fn):
    try:
        fn()
    except WalkForwardError:
        return True
    return False

observations = []
for i in range(180):
    cycle = i % 12
    base = Decimal("0.003") if cycle not in {4, 5, 10} else Decimal("-0.002")
    observations.append(ReturnObservation(
        f"2026-01-{i+1:03d}",
        base,
    ))

candidates = (
    {"lookback": 10, "threshold": "0.20"},
    {"lookback": 20, "threshold": "0.35"},
    {"lookback": 30, "threshold": "0.50"},
)

def evaluator(rows, params):
    p = dict(params)
    lookback = int(p["lookback"])
    threshold = Decimal(p["threshold"])
    # Deterministic synthetic strategy behavior.
    multiplier = Decimal("1.12") if lookback == 20 else Decimal("0.92")
    if threshold == Decimal("0.50"):
        multiplier = Decimal("0.75")
    return tuple(row.value * multiplier for row in rows)

policy = WalkForwardPolicy(
    train_size=60,
    test_size=20,
    purge_size=5,
    mode="rolling",
    annualization_factor=252,
    minimum_windows=4,
)

result = run_walk_forward_validation(observations, candidates, evaluator, policy)

check("V29.2 version verified", m.VERSION == "29.2")
check("Validation ID created", result.validation_id.startswith("WFV-"))
check("Required number of windows created", result.metrics.total_windows >= 4)
check("Candidate scores created for every window", all(len(w.candidate_scores) == 3 for w in result.windows))
check("Best candidate selected", all(w.selected_candidate_id == w.candidate_scores[0].candidate_id for w in result.windows))
check("Purge gap applied", all(w.test_start - w.train_end == 5 for w in result.windows))
check("Rolling train size retained", all(w.train_end - w.train_start == 60 for w in result.windows))
check("Out-of-sample return calculated", all(w.out_of_sample_return_pct.is_finite() for w in result.windows))
check("Out-of-sample Sharpe calculated", all(w.out_of_sample_sharpe.is_finite() for w in result.windows))
check("Out-of-sample drawdown calculated", all(w.out_of_sample_drawdown_pct <= Decimal("0") for w in result.windows))
check("Degradation calculated", all(w.degradation_pct.is_finite() for w in result.windows))
check("Profitable-window ratio calculated", Decimal("0") <= result.metrics.profitable_window_ratio <= Decimal("1"))
check("Average in-sample return calculated", result.metrics.average_in_sample_return_pct.is_finite())
check("Average out-of-sample return calculated", result.metrics.average_out_of_sample_return_pct.is_finite())
check("Average degradation calculated", result.metrics.average_degradation_pct.is_finite())
check("Aggregate OOS Sharpe calculated", result.metrics.out_of_sample_sharpe.is_finite())
check("Aggregate OOS drawdown calculated", result.metrics.out_of_sample_max_drawdown_pct <= Decimal("0"))
check("Parameter stability calculated", Decimal("0") <= result.metrics.parameter_stability_ratio <= Decimal("1"))
check("Overfitting risk calculated", Decimal("0") <= result.metrics.overfitting_risk_score <= Decimal("100"))
check("Validation status calculated", isinstance(result.metrics.validation_passed, bool))
check("Window hashes verified", all(verify_window(w) for w in result.windows))
check("Result hash verified", verify_result(result))
check("Deterministic result returned", result == run_walk_forward_validation(observations, candidates, evaluator, policy))

expanding = run_walk_forward_validation(
    observations,
    candidates,
    evaluator,
    replace(policy, mode="expanding"),
)
check("Expanding mode completed", expanding.metrics.total_windows == result.metrics.total_windows)
check("Expanding train window grows", expanding.windows[-1].train_end - expanding.windows[-1].train_start > 60)

check("Insufficient data blocked", blocked(lambda: run_walk_forward_validation(observations[:50], candidates, evaluator, policy)))
check("Single candidate blocked", blocked(lambda: run_walk_forward_validation(observations, candidates[:1], evaluator, policy)))
check("Duplicate candidates blocked", blocked(lambda: run_walk_forward_validation(observations, (candidates[0], candidates[0]), evaluator, policy)))
check("Invalid return blocked", blocked(lambda: run_walk_forward_validation(
    [replace(observations[0], value=Decimal("-1"))] + observations[1:], candidates, evaluator, policy
)))
check("Duplicate timestamp blocked", blocked(lambda: run_walk_forward_validation(
    [observations[0], replace(observations[1], timestamp=observations[0].timestamp)] + observations[2:], candidates, evaluator, policy
)))
check("Invalid train size blocked", blocked(lambda: WalkForwardPolicy(train_size=1)))
check("Invalid test size blocked", blocked(lambda: WalkForwardPolicy(test_size=0)))
check("Invalid purge size blocked", blocked(lambda: WalkForwardPolicy(purge_size=-1)))
check("Invalid mode blocked", blocked(lambda: WalkForwardPolicy(mode="bad")))

def bad_evaluator(rows, params):
    return (Decimal("0.01"),)

check("Evaluator length mismatch blocked", blocked(lambda: run_walk_forward_validation(
    observations, candidates, bad_evaluator, policy
)))

tampered_window = replace(result.windows[0], out_of_sample_return_pct=Decimal("999"))
check("Tampered window detected", blocked(lambda: verify_window(tampered_window)))

tampered_result = replace(result, result_hash="BROKEN")
check("Tampered result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "walk_forward.json"
    save_result(result, path)
    loaded = load_result(path)
    check("Walk-forward save and load passed", loaded == result)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metrics"]["overfitting_risk_score"] = "999"
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved result blocked", blocked(lambda: load_result(path)))

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

print("=" * 122)
print("V29.2 walk-forward validation engine test completed successfully.")
print("Rolling/expanding windows, purge gaps, candidate selection,")
print("in-sample/out-of-sample metrics, degradation, stability,")
print("overfitting risk, persistence, hashing, and tamper detection passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
