from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import tempfile

import backtest.offline_ai_pipeline_v28_0 as m
from backtest.offline_ai_pipeline_v28_0 import (
    PipelineError,
    PipelinePolicy,
    PipelineRow,
    PredictionRequest,
    run_pipeline,
    save_result,
    verify_result,
)


def check(name, condition):
    print(f"{name:<82}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except PipelineError:
        return True
    return False


def build_rows():
    rows = []
    for index in range(90):
        label = (-1, 0, 1)[index % 3]
        if label == -1:
            base = Decimal("-2")
        elif label == 0:
            base = Decimal("0")
        else:
            base = Decimal("2")

        rows.append(PipelineRow(
            row_id=f"ROW-{index:03d}",
            timestamp=f"2026-01-{index + 1:03d}T16:00:00+00:00",
            features=(
                base + Decimal(index % 5) / Decimal("20"),
                base * Decimal("0.8") + Decimal(index % 7) / Decimal("25"),
                None if index % 13 == 0 else base * Decimal("0.5"),
                Decimal(index % 11) / Decimal("10"),
                Decimal("5"),
            ),
            label=label,
        ))
    return tuple(rows)


rows = build_rows()
feature_names = ("trend", "momentum", "strength", "noise", "constant")
requests = (
    PredictionRequest("P-BUY", "2026-07-28T20:00:00-07:00", (2.2, 1.7, 1.0, 0.3, 5)),
    PredictionRequest("P-HOLD", "2026-07-28T20:01:00-07:00", (0.0, 0.1, 0.0, 0.4, 5)),
    PredictionRequest("P-SELL", "2026-07-28T20:02:00-07:00", (-2.1, -1.6, -1.0, 0.2, 5)),
)

policy = PipelinePolicy(
    validation_ratio=Decimal("0.20"),
    split_mode="TIME_SERIES",
    purge_size=2,
    random_seed=123,
    normalization="ZSCORE",
    missing_strategy="MEDIAN",
    variance_threshold=Decimal("0.000001"),
    correlation_threshold=Decimal("0.98"),
    max_features=4,
    learning_rate=Decimal("0.10"),
    epochs=600,
    l2_strength=Decimal("0.001"),
    patience=40,
    min_confidence=Decimal("0.50"),
    min_margin=Decimal("0.05"),
    max_entropy=Decimal("0.95"),
    hold_label=0,
)

result = run_pipeline(rows, feature_names, requests, policy)

check("V28.0 engine version verified", m.VERSION == "28.0")
check("Experiment ID created", result.experiment_id.startswith("EXP-"))
check("Training partition created", len(result.train_ids) > 0)
check("Validation partition created", len(result.validation_ids) > 0)
check("Purge partition created", len(result.purged_ids) == 2)
check("No train/validation leakage", not (set(result.train_ids) & set(result.validation_ids)))
check("Normalization statistics created", len(result.model.feature_stats) == len(feature_names))
check("Constant feature removed", "constant" not in result.selected_feature_names)
check("Feature selection completed", 1 <= len(result.selected_feature_names) <= 4)
check("Multiclass model trained", result.model.classes == (-1, 0, 1))
check("Model weights created", len(result.model.weights) == 3)
check("Training accuracy calculated", result.train_accuracy >= Decimal("0.85"))
check("Validation accuracy calculated", result.validation_accuracy >= Decimal("0.80"))
check("Validation log loss calculated", result.validation_log_loss >= Decimal("0"))
check("Three predictions created", len(result.predictions) == 3)
check("BUY prediction generated", result.predictions[0].final_label == 1)
check("HOLD prediction generated", result.predictions[1].final_label == 0)
check("SELL prediction generated", result.predictions[2].final_label == -1)
check("Prediction probabilities sum to one", all(
    sum(item.probabilities) == Decimal("1.000000")
    for item in result.predictions
))
check("Model hash created", len(result.model.model_hash) == 64)
check("Result hash verified", verify_result(result))
check("Deterministic pipeline returned", result == run_pipeline(rows, feature_names, requests, policy))

stratified = run_pipeline(
    rows,
    feature_names,
    requests,
    replace(policy, split_mode="STRATIFIED", purge_size=0),
)
check("Stratified pipeline completed", len(stratified.validation_ids) > 0)

strict_result = run_pipeline(
    rows,
    feature_names,
    (
        PredictionRequest("P-UNCERTAIN", "2026-07-28T20:03:00-07:00", (0.7, 0.5, 0.2, 0.9, 5)),
    ),
    replace(policy, min_confidence=Decimal("0.99"), min_margin=Decimal("0.99")),
)
check("Low-confidence HOLD override applied", strict_result.predictions[0].final_label == 0)
check("Low-confidence reasons recorded", bool(strict_result.predictions[0].reason_codes))

check("Duplicate feature names blocked", blocked(lambda: run_pipeline(
    rows,
    ("a", "a", "c", "d", "e"),
    requests,
    policy,
)))
check("Duplicate row IDs blocked", blocked(lambda: run_pipeline(
    rows + (rows[0],),
    feature_names,
    requests,
    policy,
)))
check("Feature-width mismatch blocked", blocked(lambda: run_pipeline(
    rows,
    feature_names[:-1],
    requests,
    policy,
)))
check("Duplicate prediction IDs blocked", blocked(lambda: run_pipeline(
    rows,
    feature_names,
    (requests[0], requests[0]),
    policy,
)))
check("Invalid policy blocked", blocked(lambda: PipelinePolicy(validation_ratio=1)))
check("All-missing feature blocked", blocked(lambda: run_pipeline(
    tuple(replace(row, features=row.features[:-1] + (None,)) for row in rows),
    feature_names,
    requests,
    policy,
)))

tampered = replace(result, validation_accuracy=Decimal("0"))
check("Tampered result detected", blocked(lambda: verify_result(tampered)))

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "pipeline_result.json"
    save_result(result, path)
    check("Pipeline result saved", path.exists())

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
print("V28.0 offline AI pipeline orchestrator test completed successfully.")
print("Split, train-only normalization, feature selection, multiclass training,")
print("prediction, confidence gating, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
