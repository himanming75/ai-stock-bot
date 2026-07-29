from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_hyperopt_v28_4 as m
from backtest.offline_hyperopt_v28_4 import (
    HyperoptError,
    SearchPolicy,
    generate_combinations,
    load_result,
    run_search,
    save_result,
    validate_search_space,
    verify_result,
    verify_trial,
)


def check(name, condition):
    print(f"{name:<88}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except HyperoptError:
        return True
    return False


space = {
    "learning_rate": (Decimal("0.01"), Decimal("0.05"), Decimal("0.10")),
    "depth": (2, 3),
    "trees": (50, 100),
}

def objective(params):
    lr = Decimal(params["learning_rate"])
    depth = Decimal(params["depth"])
    trees = Decimal(params["trees"])
    return (
        Decimal("0.70")
        + (Decimal("0.10") - abs(lr - Decimal("0.05")))
        + Decimal("0.02") * depth
        + Decimal("0.0002") * trees
    )

validated = validate_search_space(space)
combinations = generate_combinations(space)
grid = run_search(
    space,
    objective,
    SearchPolicy(
        mode="GRID",
        max_trials=100,
        random_seed=42,
        early_stopping_rounds=0,
    ),
)
random_result = run_search(
    space,
    objective,
    SearchPolicy(
        mode="RANDOM",
        max_trials=5,
        random_seed=123,
        early_stopping_rounds=0,
    ),
)

check("V28.4 engine version verified", m.VERSION == "28.4")
check("Parameter space validated", len(validated) == 3)
check("Parameter combinations generated", len(combinations) == 12)
check("Grid search completed", grid.mode == "GRID")
check("Random search completed", random_result.mode == "RANDOM")
check("Grid search evaluated all combinations", len(grid.trials) == 12)
check("Random search respected max trials", len(random_result.trials) == 5)
check("Trial IDs generated", all(t.trial_id.startswith("TRIAL-") for t in grid.trials))
check("Parameter hashes verified", all(verify_trial(t) for t in grid.trials))
check("Validation scores recorded", all(isinstance(t.score, Decimal) for t in grid.trials))
check("Ranking created", grid.ranking[0] == grid.best_trial_id)
check("Best parameter selected", dict(grid.best_parameters)["learning_rate"] == "0.05")
check("Search history recorded", len(grid.trials) == len(grid.ranking))
check("Result hash verified", verify_result(grid))
check("Deterministic grid search returned", grid == run_search(
    space,
    objective,
    SearchPolicy(mode="GRID", max_trials=100, random_seed=42),
))
check("Deterministic random search returned", random_result == run_search(
    space,
    objective,
    SearchPolicy(mode="RANDOM", max_trials=5, random_seed=123),
))

flat_space = {
    "learning_rate": (Decimal("0.01"), Decimal("0.02"), Decimal("0.03"), Decimal("0.04")),
    "depth": (2,),
}
early = run_search(
    flat_space,
    lambda params: Decimal("0.50"),
    SearchPolicy(
        mode="GRID",
        max_trials=10,
        early_stopping_rounds=2,
        min_improvement=Decimal("0.000001"),
    ),
)
check("Early stopping triggered", early.early_stopped)
check("Early stopping reduced trials", len(early.trials) < len(generate_combinations(flat_space)))

check("Invalid learning rate blocked", blocked(lambda: validate_search_space({
    "learning_rate": (0,),
})))
check("Invalid depth blocked", blocked(lambda: validate_search_space({
    "depth": (0,),
})))
check("Invalid tree count blocked", blocked(lambda: validate_search_space({
    "trees": (0,),
})))
check("Duplicate parameter value blocked", blocked(lambda: validate_search_space({
    "learning_rate": (Decimal("0.01"), Decimal("0.01")),
})))
check("Empty parameter values blocked", blocked(lambda: validate_search_space({
    "learning_rate": (),
})))
check("Invalid search mode blocked", blocked(lambda: SearchPolicy(mode="BAD")))
check("Invalid max trials blocked", blocked(lambda: SearchPolicy(max_trials=0)))

tampered_trial = replace(grid.trials[0], score=Decimal("999"))
check("Tampered trial detected", blocked(lambda: verify_trial(tampered_trial)))

tampered_result = replace(grid, best_trial_id=grid.ranking[-1])
check("Tampered result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "hyperopt.json"
    save_result(grid, path)
    loaded = load_result(path)
    check("Search save and load passed", loaded == grid)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["best_trial_id"] = grid.ranking[-1]
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved search blocked", blocked(lambda: load_result(path)))

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

print("=" * 108)
print("V28.4 offline hyperparameter optimization test completed successfully.")
print("Grid search, random search, parameter validation, ranking, best selection,")
print("early stopping, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
