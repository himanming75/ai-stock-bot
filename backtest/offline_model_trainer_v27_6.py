from __future__ import annotations

"""
V27.6 Offline Model Trainer

A deterministic, dependency-free multinomial logistic-regression trainer
for normalized and selected feature data.

Features:
- multiclass softmax logistic regression
- deterministic gradient-descent training
- class-weight balancing
- L2 regularization
- early stopping
- train and validation metrics
- confusion matrix and per-class statistics
- probability prediction
- model registry metadata
- SHA-256 model and result integrity
- JSON save/load and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import exp, log
from pathlib import Path
from typing import Any, Iterable
import json
import random

VERSION = "27.6"
ZERO = Decimal("0")
SIX = Decimal("0.000001")


class ModelError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ModelError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ModelError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TrainingRow:
    row_id: str
    features: tuple[Decimal, ...]
    label: int


@dataclass(frozen=True)
class TrainerPolicy:
    learning_rate: Decimal = Decimal("0.08")
    epochs: int = 500
    l2_strength: Decimal = Decimal("0.001")
    tolerance: Decimal = Decimal("0.000001")
    patience: int = 30
    class_weight_mode: str = "BALANCED"
    random_seed: int = 42

    def __post_init__(self) -> None:
        if _d(self.learning_rate) <= ZERO:
            raise ModelError("learning_rate must be positive")
        if self.epochs <= 0:
            raise ModelError("epochs must be positive")
        if _d(self.l2_strength) < ZERO:
            raise ModelError("l2_strength cannot be negative")
        if _d(self.tolerance) < ZERO:
            raise ModelError("tolerance cannot be negative")
        if self.patience <= 0:
            raise ModelError("patience must be positive")
        if self.class_weight_mode.upper() not in {"NONE", "BALANCED"}:
            raise ModelError("unsupported class_weight_mode")


@dataclass(frozen=True)
class ClassMetric:
    label: int
    precision: Decimal
    recall: Decimal
    f1: Decimal
    support: int


@dataclass(frozen=True)
class ModelArtifact:
    version: str
    model_type: str
    feature_count: int
    classes: tuple[int, ...]
    weights: tuple[tuple[Decimal, ...], ...]
    biases: tuple[Decimal, ...]
    policy: TrainerPolicy
    epochs_completed: int
    training_loss: Decimal
    model_hash: str


@dataclass(frozen=True)
class TrainingResult:
    version: str
    train_accuracy: Decimal
    validation_accuracy: Decimal
    validation_log_loss: Decimal
    confusion_matrix: tuple[tuple[int, ...], ...]
    class_metrics: tuple[ClassMetric, ...]
    model: ModelArtifact
    input_hash: str
    result_hash: str


def _policy_payload(policy: TrainerPolicy) -> dict[str, Any]:
    return {
        "learning_rate": str(policy.learning_rate),
        "epochs": policy.epochs,
        "l2_strength": str(policy.l2_strength),
        "tolerance": str(policy.tolerance),
        "patience": policy.patience,
        "class_weight_mode": policy.class_weight_mode.upper(),
        "random_seed": policy.random_seed,
    }


def _model_payload(model: ModelArtifact, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": model.version,
        "model_type": model.model_type,
        "feature_count": model.feature_count,
        "classes": list(model.classes),
        "weights": [[str(value) for value in row] for row in model.weights],
        "biases": [str(value) for value in model.biases],
        "policy": _policy_payload(model.policy),
        "epochs_completed": model.epochs_completed,
        "training_loss": str(model.training_loss),
    }
    if include_hash:
        payload["model_hash"] = model.model_hash
    return payload


def _metric_payload(metric: ClassMetric) -> dict[str, Any]:
    return {
        "label": metric.label,
        "precision": str(metric.precision),
        "recall": str(metric.recall),
        "f1": str(metric.f1),
        "support": metric.support,
    }


def _result_payload(result: TrainingResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "train_accuracy": str(result.train_accuracy),
        "validation_accuracy": str(result.validation_accuracy),
        "validation_log_loss": str(result.validation_log_loss),
        "confusion_matrix": [list(row) for row in result.confusion_matrix],
        "class_metrics": [_metric_payload(metric) for metric in result.class_metrics],
        "model": _model_payload(result.model, include_hash=True),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_rows(items: Iterable[TrainingRow], expected_width: int | None = None) -> tuple[TrainingRow, ...]:
    rows = []
    width = expected_width
    for item in items:
        row_id = item.row_id.strip()
        if not row_id:
            raise ModelError("row_id is required")
        if width is None:
            width = len(item.features)
        if width <= 0 or len(item.features) != width:
            raise ModelError("inconsistent feature width")
        values = tuple(_q(value) for value in item.features)
        rows.append(TrainingRow(row_id, values, int(item.label)))

    if not rows:
        raise ModelError("training rows cannot be empty")
    if len({row.row_id for row in rows}) != len(rows):
        raise ModelError("duplicate row IDs detected")
    return tuple(rows)


def _softmax(logits: list[float]) -> list[float]:
    maximum = max(logits)
    values = [exp(value - maximum) for value in logits]
    total = sum(values)
    return [value / total for value in values]


def _predict_probabilities_raw(
    features: tuple[Decimal, ...],
    weights: list[list[float]],
    biases: list[float],
) -> list[float]:
    logits = []
    for class_index, class_weights in enumerate(weights):
        logits.append(
            sum(float(value) * weight for value, weight in zip(features, class_weights))
            + biases[class_index]
        )
    return _softmax(logits)


def _class_weights(rows: tuple[TrainingRow, ...], classes: tuple[int, ...], mode: str) -> dict[int, float]:
    if mode == "NONE":
        return {label: 1.0 for label in classes}
    counts = {label: sum(1 for row in rows if row.label == label) for label in classes}
    total = len(rows)
    return {
        label: total / (len(classes) * counts[label])
        for label in classes
    }


def _loss(
    rows: tuple[TrainingRow, ...],
    classes: tuple[int, ...],
    weights: list[list[float]],
    biases: list[float],
    class_weights: dict[int, float],
    l2: float,
) -> float:
    class_index = {label: index for index, label in enumerate(classes)}
    total = 0.0
    total_weight = 0.0
    for row in rows:
        probabilities = _predict_probabilities_raw(row.features, weights, biases)
        weight = class_weights[row.label]
        total -= weight * log(max(probabilities[class_index[row.label]], 1e-15))
        total_weight += weight
    penalty = 0.5 * l2 * sum(value * value for class_row in weights for value in class_row)
    return total / total_weight + penalty


def train_model(
    train_rows: Iterable[TrainingRow],
    validation_rows: Iterable[TrainingRow],
    policy: TrainerPolicy | None = None,
) -> TrainingResult:
    selected = policy or TrainerPolicy()
    train = _normalize_rows(train_rows)
    validation = _normalize_rows(validation_rows, len(train[0].features))

    overlap = {row.row_id for row in train} & {row.row_id for row in validation}
    if overlap:
        raise ModelError("train/validation leakage detected")

    classes = tuple(sorted({row.label for row in train}))
    if len(classes) < 2:
        raise ModelError("at least two training classes are required")
    if not set(row.label for row in validation).issubset(set(classes)):
        raise ModelError("validation contains unseen class")

    feature_count = len(train[0].features)
    class_index = {label: index for index, label in enumerate(classes)}
    rng = random.Random(selected.random_seed)
    weights = [
        [rng.uniform(-0.01, 0.01) for _ in range(feature_count)]
        for _ in classes
    ]
    biases = [0.0 for _ in classes]
    class_weights = _class_weights(train, classes, selected.class_weight_mode.upper())

    learning_rate = float(selected.learning_rate)
    l2 = float(selected.l2_strength)
    tolerance = float(selected.tolerance)
    best_loss = float("inf")
    best_weights = [row[:] for row in weights]
    best_biases = biases[:]
    no_improvement = 0
    epochs_completed = 0

    for epoch in range(1, selected.epochs + 1):
        grad_w = [[0.0] * feature_count for _ in classes]
        grad_b = [0.0] * len(classes)
        total_weight = 0.0

        for row in train:
            probabilities = _predict_probabilities_raw(row.features, weights, biases)
            target_index = class_index[row.label]
            sample_weight = class_weights[row.label]
            total_weight += sample_weight

            for class_pos in range(len(classes)):
                error = (probabilities[class_pos] - (1.0 if class_pos == target_index else 0.0)) * sample_weight
                grad_b[class_pos] += error
                for feature_pos, feature_value in enumerate(row.features):
                    grad_w[class_pos][feature_pos] += error * float(feature_value)

        for class_pos in range(len(classes)):
            biases[class_pos] -= learning_rate * grad_b[class_pos] / total_weight
            for feature_pos in range(feature_count):
                gradient = grad_w[class_pos][feature_pos] / total_weight + l2 * weights[class_pos][feature_pos]
                weights[class_pos][feature_pos] -= learning_rate * gradient

        current_loss = _loss(train, classes, weights, biases, class_weights, l2)
        epochs_completed = epoch

        if best_loss - current_loss > tolerance:
            best_loss = current_loss
            best_weights = [row[:] for row in weights]
            best_biases = biases[:]
            no_improvement = 0
        else:
            no_improvement += 1
            if no_improvement >= selected.patience:
                break

    model = ModelArtifact(
        version=VERSION,
        model_type="MULTINOMIAL_LOGISTIC_REGRESSION",
        feature_count=feature_count,
        classes=classes,
        weights=tuple(tuple(_q(value) for value in row) for row in best_weights),
        biases=tuple(_q(value) for value in best_biases),
        policy=selected,
        epochs_completed=epochs_completed,
        training_loss=_q(best_loss),
        model_hash="",
    )
    model = replace(model, model_hash=_hash(_model_payload(model)))

    train_predictions = predict_many(model, [row.features for row in train])
    validation_predictions = predict_many(model, [row.features for row in validation])
    train_accuracy = _accuracy([row.label for row in train], train_predictions)
    validation_accuracy = _accuracy([row.label for row in validation], validation_predictions)
    validation_log_loss = _validation_log_loss(model, validation)
    matrix = _confusion(classes, [row.label for row in validation], validation_predictions)
    metrics = _class_metrics(classes, matrix)

    input_hash = _hash({
        "train": [
            {"row_id": row.row_id, "features": [str(v) for v in row.features], "label": row.label}
            for row in train
        ],
        "validation": [
            {"row_id": row.row_id, "features": [str(v) for v in row.features], "label": row.label}
            for row in validation
        ],
        "policy": _policy_payload(selected),
    })

    result = TrainingResult(
        version=VERSION,
        train_accuracy=_q(train_accuracy),
        validation_accuracy=_q(validation_accuracy),
        validation_log_loss=_q(validation_log_loss),
        confusion_matrix=matrix,
        class_metrics=metrics,
        model=model,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def predict_proba(model: ModelArtifact, features: Iterable[Any]) -> tuple[Decimal, ...]:
    verify_model(model)
    values = tuple(_q(value) for value in features)
    if len(values) != model.feature_count:
        raise ModelError("prediction feature width mismatch")
    probabilities = _predict_probabilities_raw(
        values,
        [[float(value) for value in row] for row in model.weights],
        [float(value) for value in model.biases],
    )
    quantized = [_q(value) for value in probabilities]
    difference = Decimal("1.000000") - sum(quantized, ZERO)
    quantized[-1] += difference
    return tuple(quantized)


def predict(model: ModelArtifact, features: Iterable[Any]) -> int:
    probabilities = predict_proba(model, features)
    best = max(range(len(probabilities)), key=lambda index: (probabilities[index], -index))
    return model.classes[best]


def predict_many(model: ModelArtifact, rows: Iterable[Iterable[Any]]) -> tuple[int, ...]:
    return tuple(predict(model, row) for row in rows)


def _accuracy(actual: list[int], predicted: tuple[int, ...]) -> Decimal:
    correct = sum(1 for left, right in zip(actual, predicted) if left == right)
    return _d(correct) / _d(len(actual))


def _validation_log_loss(model: ModelArtifact, rows: tuple[TrainingRow, ...]) -> Decimal:
    class_index = {label: index for index, label in enumerate(model.classes)}
    total = 0.0
    for row in rows:
        probabilities = predict_proba(model, row.features)
        total -= log(max(float(probabilities[class_index[row.label]]), 1e-15))
    return _d(total / len(rows))


def _confusion(
    classes: tuple[int, ...],
    actual: list[int],
    predicted: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    index = {label: pos for pos, label in enumerate(classes)}
    matrix = [[0 for _ in classes] for _ in classes]
    for left, right in zip(actual, predicted):
        matrix[index[left]][index[right]] += 1
    return tuple(tuple(row) for row in matrix)


def _class_metrics(
    classes: tuple[int, ...],
    matrix: tuple[tuple[int, ...], ...],
) -> tuple[ClassMetric, ...]:
    output = []
    for index, label in enumerate(classes):
        tp = matrix[index][index]
        fp = sum(matrix[row][index] for row in range(len(classes))) - tp
        fn = sum(matrix[index]) - tp
        support = sum(matrix[index])
        precision = Decimal(tp) / Decimal(tp + fp) if tp + fp else ZERO
        recall = Decimal(tp) / Decimal(tp + fn) if tp + fn else ZERO
        f1 = (
            Decimal("2") * precision * recall / (precision + recall)
            if precision + recall else ZERO
        )
        output.append(ClassMetric(label, _q(precision), _q(recall), _q(f1), support))
    return tuple(output)


def verify_model(model: ModelArtifact) -> bool:
    if model.version != VERSION:
        raise ModelError("unsupported model version")
    if model.model_type != "MULTINOMIAL_LOGISTIC_REGRESSION":
        raise ModelError("unsupported model type")
    if model.feature_count <= 0:
        raise ModelError("feature_count must be positive")
    if len(model.classes) < 2 or len(model.classes) != len(set(model.classes)):
        raise ModelError("invalid model classes")
    if len(model.weights) != len(model.classes) or len(model.biases) != len(model.classes):
        raise ModelError("model class parameter mismatch")
    if any(len(row) != model.feature_count for row in model.weights):
        raise ModelError("model feature parameter mismatch")
    clean = replace(model, model_hash="")
    if model.model_hash != _hash(_model_payload(clean)):
        raise ModelError("model hash mismatch")
    return True


def verify_result(result: TrainingResult) -> bool:
    if result.version != VERSION:
        raise ModelError("unsupported training-result version")
    verify_model(result.model)
    class_count = len(result.model.classes)
    if len(result.confusion_matrix) != class_count:
        raise ModelError("confusion matrix size mismatch")
    if any(len(row) != class_count for row in result.confusion_matrix):
        raise ModelError("confusion matrix width mismatch")
    if len(result.class_metrics) != class_count:
        raise ModelError("class metric count mismatch")
    if not (ZERO <= result.train_accuracy <= Decimal("1")):
        raise ModelError("train accuracy out of range")
    if not (ZERO <= result.validation_accuracy <= Decimal("1")):
        raise ModelError("validation accuracy out of range")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise ModelError("training result hash mismatch")
    return True


def save_model(model: ModelArtifact, path: str | Path) -> Path:
    verify_model(model)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_model_payload(model, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_model(path: str | Path) -> ModelArtifact:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    policy_data = payload["policy"]
    policy = TrainerPolicy(
        learning_rate=_d(policy_data["learning_rate"]),
        epochs=int(policy_data["epochs"]),
        l2_strength=_d(policy_data["l2_strength"]),
        tolerance=_d(policy_data["tolerance"]),
        patience=int(policy_data["patience"]),
        class_weight_mode=policy_data["class_weight_mode"],
        random_seed=int(policy_data["random_seed"]),
    )
    model = ModelArtifact(
        version=payload["version"],
        model_type=payload["model_type"],
        feature_count=int(payload["feature_count"]),
        classes=tuple(int(value) for value in payload["classes"]),
        weights=tuple(tuple(_d(value) for value in row) for row in payload["weights"]),
        biases=tuple(_d(value) for value in payload["biases"]),
        policy=policy,
        epochs_completed=int(payload["epochs_completed"]),
        training_loss=_d(payload["training_loss"]),
        model_hash=payload["model_hash"],
    )
    verify_model(model)
    return model


def save_result(result: TrainingResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
