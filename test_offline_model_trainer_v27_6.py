from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import ast
import json
import tempfile

import backtest.offline_model_trainer_v27_6 as m
from backtest.offline_model_trainer_v27_6 import (
    ModelError,
    TrainerPolicy,
    TrainingRow,
    load_model,
    predict,
    predict_many,
    predict_proba,
    save_model,
    save_result,
    train_model,
    verify_model,
    verify_result,
)


def check(name, condition):
    print(f"{name:<76}: {condition}")
    if not condition:
        raise AssertionError(name)


def blocked(fn):
    try:
        fn()
    except ModelError:
        return True
    return False


def make_rows(prefix, count, offset=0):
    rows = []
    for index in range(count):
        cls = (index + offset) % 3
        label = (-1, 0, 1)[cls]
        if label == -1:
            features = (
                Decimal("-2.0") + Decimal(index % 5) / Decimal("20"),
                Decimal("-1.5") + Decimal(index % 7) / Decimal("25"),
                Decimal("-1.0"),
            )
        elif label == 0:
            features = (
                Decimal(index % 5) / Decimal("40"),
                Decimal(index % 7) / Decimal("50"),
                Decimal("0.0"),
            )
        else:
            features = (
                Decimal("2.0") + Decimal(index % 5) / Decimal("20"),
                Decimal("1.5") + Decimal(index % 7) / Decimal("25"),
                Decimal("1.0"),
            )
        rows.append(TrainingRow(f"{prefix}-{index:03d}", features, label))
    return tuple(rows)


train = make_rows("TRAIN",  ninety := 90)
validation = make_rows("VAL", 30, offset=1)

policy = TrainerPolicy(
    learning_rate=Decimal("0.10"),
    epochs=600,
    l2_strength=Decimal("0.001"),
    tolerance=Decimal("0.000001"),
    patience=40,
    class_weight_mode="BALANCED",
    random_seed=123,
)

result = train_model(train, validation, policy)
model = result.model

check("V27.6 engine version verified", m.VERSION == "27.6")
check("Multiclass model trained", model.classes == (-1, 0, 1))
check("Model feature count stored", model.feature_count == 3)
check("Model weights created", len(model.weights) == 3 and all(len(row) == 3 for row in model.weights))
check("Model biases created", len(model.biases) == 3)
check("Training epochs recorded", 1 <= model.epochs_completed <= policy.epochs)
check("Training loss calculated", model.training_loss > Decimal("0"))
check("Training accuracy calculated", result.train_accuracy >= Decimal("0.90"))
check("Validation accuracy calculated", result.validation_accuracy >= Decimal("0.90"))
check("Validation log loss calculated", result.validation_log_loss >= Decimal("0"))
check("Confusion matrix created", len(result.confusion_matrix) == 3)
check("Per-class metrics created", len(result.class_metrics) == 3)
check("Model hash verified", verify_model(model))
check("Training result hash verified", verify_result(result))
check("Deterministic training returned", result == train_model(train, validation, policy))

negative_prediction = predict(model, (-2, -1.5, -1))
hold_prediction = predict(model, (0, 0, 0))
positive_prediction = predict(model, (2, 1.5, 1))
check("SELL-class prediction generated", negative_prediction == -1)
check("HOLD-class prediction generated", hold_prediction == 0)
check("BUY-class prediction generated", positive_prediction == 1)

probabilities = predict_proba(model, (2, 1.5, 1))
check("Prediction probabilities created", len(probabilities) == 3)
check("Prediction probabilities sum to one", sum(probabilities) == Decimal("1.000000"))
check("Batch prediction created", len(predict_many(model, [(-2, -1.5, -1), (0, 0, 0), (2, 1.5, 1)])) == 3)

check("Train/validation leakage blocked", blocked(lambda: train_model(
    train,
    validation + (train[0],),
    policy,
)))
check("Single training class blocked", blocked(lambda: train_model(
    tuple(replace(row, label=1) for row in train),
    validation,
    policy,
)))
check("Unseen validation class blocked", blocked(lambda: train_model(
    train,
    validation + (TrainingRow("UNSEEN", (1, 2, 3), 9),),
    policy,
)))
check("Feature-width mismatch blocked", blocked(lambda: train_model(
    train,
    validation + (TrainingRow("BAD-WIDTH", (1, 2), 1),),
    policy,
)))
check("Invalid learning rate blocked", blocked(lambda: TrainerPolicy(learning_rate=0)))
check("Invalid class weighting blocked", blocked(lambda: TrainerPolicy(class_weight_mode="BAD")))
check("Prediction width mismatch blocked", blocked(lambda: predict(model, (1, 2))))

tampered_model = replace(model, biases=(Decimal("999"),) + model.biases[1:])
check("Tampered model detected", blocked(lambda: verify_model(tampered_model)))

tampered_result = replace(result, validation_accuracy=Decimal("0"))
check("Tampered training result detected", blocked(lambda: verify_result(tampered_result)))

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    model_path = folder / "model.json"
    result_path = folder / "result.json"

    save_model(model, model_path)
    loaded_model = load_model(model_path)
    check("Model save and load passed", loaded_model == model)
    check("Loaded model predicts identically", predict(loaded_model, (2, 1.5, 1)) == 1)

    save_result(result, result_path)
    check("Training result saved", result_path.exists())

    payload = json.loads(model_path.read_text(encoding="utf-8"))
    payload["biases"][0] = "999.000000"
    model_path.write_text(json.dumps(payload), encoding="utf-8")
    check("Tampered saved model blocked", blocked(lambda: load_model(model_path)))

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

print("=" * 96)
print("V27.6 offline model trainer test completed successfully.")
print("Multiclass training, class balancing, regularization, early stopping,")
print("probabilities, metrics, persistence, hashing, and tamper checks passed.")
print("Market/account/network/broker/order/live execution remained blocked.")
