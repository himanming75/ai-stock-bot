from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_experiment_manager_v28_1 as m
from backtest.offline_experiment_manager_v28_1 import (
    ExperimentError,
    ExperimentMetrics,
    add_experiment,
    compare_experiments,
    create_experiment,
    create_registry,
    load_registry,
    save_registry,
    verify_record,
    verify_registry,
)


def check(name, condition):
    print(f"{name:<82}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except ExperimentError:
        return True
    return False


exp1 = create_experiment(
    pipeline_version="28.0",
    model_hash="a" * 64,
    dataset_hash="1" * 64,
    feature_names=("trend", "momentum", "rsi"),
    hyperparameters={
        "learning_rate": "0.08",
        "epochs": 500,
        "l2": "0.001",
        "seed": 42,
    },
    metrics=ExperimentMetrics(
        accuracy=Decimal("0.78"),
        precision=Decimal("0.76"),
        recall=Decimal("0.75"),
        f1=Decimal("0.755"),
        validation_loss=Decimal("0.52"),
        sharpe=Decimal("1.20"),
        total_return_pct=Decimal("12.5"),
        max_drawdown_pct=Decimal("-8.0"),
    ),
)

exp2 = create_experiment(
    pipeline_version="28.0",
    model_hash="b" * 64,
    dataset_hash="1" * 64,
    feature_names=("trend", "momentum", "rsi", "atr"),
    hyperparameters={
        "learning_rate": "0.10",
        "epochs": 650,
        "l2": "0.0005",
        "seed": 42,
    },
    metrics=ExperimentMetrics(
        accuracy=Decimal("0.84"),
        precision=Decimal("0.82"),
        recall=Decimal("0.81"),
        f1=Decimal("0.815"),
        validation_loss=Decimal("0.41"),
        sharpe=Decimal("1.65"),
        total_return_pct=Decimal("18.2"),
        max_drawdown_pct=Decimal("-7.0"),
    ),
)

exp3 = create_experiment(
    pipeline_version="28.0",
    model_hash="c" * 64,
    dataset_hash="2" * 64,
    feature_names=("trend", "momentum"),
    hyperparameters={
        "learning_rate": "0.05",
        "epochs": 400,
        "l2": "0.002",
        "seed": 7,
    },
    metrics=ExperimentMetrics(
        accuracy=Decimal("0.72"),
        precision=Decimal("0.70"),
        recall=Decimal("0.69"),
        f1=Decimal("0.695"),
        validation_loss=Decimal("0.63"),
        sharpe=Decimal("0.80"),
        total_return_pct=Decimal("8.0"),
        max_drawdown_pct=Decimal("-10.0"),
    ),
)

registry = create_registry((exp1, exp2))
comparison = compare_experiments(exp2, exp1)

check("V28.1 engine version verified", m.VERSION == "28.1")
check("Experiment ID created", exp1.experiment_id.startswith("EXP-"))
check("Hyperparameters stored", dict(exp1.hyperparameters)["epochs"] == "500")
check("Metrics stored", exp1.metrics.accuracy == Decimal("0.780000"))
check("Experiment score calculated", exp1.score != Decimal("0"))
check("Experiment record hash verified", verify_record(exp1))
check("Registry created", len(registry.experiments) == 2)
check("Best model selected", registry.best_experiment_id == exp2.experiment_id)
check("Ranking calculated", registry.ranking[0] == exp2.experiment_id)
check("Previous experiment compared", comparison.current_id == exp2.experiment_id)
check("Improvement detected", comparison.improved)
check("Positive score delta calculated", comparison.score_delta > Decimal("0"))
check("Registry hash verified", verify_registry(registry))
check("Deterministic experiment returned", exp1 == create_experiment(
    pipeline_version="28.0",
    model_hash="a" * 64,
    dataset_hash="1" * 64,
    feature_names=("trend", "momentum", "rsi"),
    hyperparameters={
        "learning_rate": "0.08",
        "epochs": 500,
        "l2": "0.001",
        "seed": 42,
    },
    metrics=ExperimentMetrics(
        accuracy=Decimal("0.78"),
        precision=Decimal("0.76"),
        recall=Decimal("0.75"),
        f1=Decimal("0.755"),
        validation_loss=Decimal("0.52"),
        sharpe=Decimal("1.20"),
        total_return_pct=Decimal("12.5"),
        max_drawdown_pct=Decimal("-8.0"),
    ),
))

expanded = add_experiment(registry, exp3)
check("Experiment added to registry", len(expanded.experiments) == 3)
check("Best model preserved after weaker run", expanded.best_experiment_id == exp2.experiment_id)

check("Duplicate experiment blocked", blocked(lambda: add_experiment(registry, exp1)))
check("Invalid model hash blocked", blocked(lambda: create_experiment(
    pipeline_version="28.0",
    model_hash="BAD",
    dataset_hash="1" * 64,
    feature_names=("a",),
    hyperparameters={"epochs": 1},
    metrics=exp1.metrics,
)))
check("Duplicate feature names blocked", blocked(lambda: create_experiment(
    pipeline_version="28.0",
    model_hash="d" * 64,
    dataset_hash="3" * 64,
    feature_names=("a", "a"),
    hyperparameters={"epochs": 1},
    metrics=exp1.metrics,
)))
check("Invalid accuracy blocked", blocked(lambda: create_experiment(
    pipeline_version="28.0",
    model_hash="d" * 64,
    dataset_hash="3" * 64,
    feature_names=("a",),
    hyperparameters={"epochs": 1},
    metrics=replace(exp1.metrics, accuracy=Decimal("1.5")),
)))
check("Positive drawdown blocked", blocked(lambda: create_experiment(
    pipeline_version="28.0",
    model_hash="d" * 64,
    dataset_hash="3" * 64,
    feature_names=("a",),
    hyperparameters={"epochs": 1},
    metrics=replace(exp1.metrics, max_drawdown_pct=Decimal("5")),
)))

tampered_record = replace(exp1, score=Decimal("999"))
check("Tampered record detected", blocked(lambda: verify_record(tampered_record)))

tampered_registry = replace(registry, best_experiment_id=exp1.experiment_id)
check("Tampered registry detected", blocked(lambda: verify_registry(tampered_registry)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "registry.json"
    save_registry(expanded, path)
    loaded = load_registry(path)
    check("Registry save and load passed", loaded == expanded)

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["best_experiment_id"] = exp3.experiment_id
    path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved registry blocked", blocked(lambda: load_registry(path)))

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

print("=" * 102)
print("V28.1 offline experiment manager test completed successfully.")
print("Experiment IDs, metrics, hyperparameters, ranking, best-model tracking,")
print("comparison, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
