from __future__ import annotations

"""
V28.0 Offline AI Pipeline Orchestrator

Purpose:
Connect the V27 research stages into one deterministic offline pipeline:

raw rows
-> split
-> fit normalization on train only
-> transform train/validation/prediction
-> feature selection on train only
-> train multiclass logistic regression
-> validation metrics
-> prediction + confidence gate
-> experiment artifact

This implementation is dependency-free and self-contained so the full
orchestrator can be tested without network or broker access.

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import exp, log, sqrt
from pathlib import Path
from typing import Any, Iterable, Sequence
import json
import random

VERSION = "28.0"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class PipelineError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise PipelineError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise PipelineError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PipelineRow:
    row_id: str
    timestamp: str
    features: tuple[Decimal | None, ...]
    label: int


@dataclass(frozen=True)
class PredictionRequest:
    prediction_id: str
    timestamp: str
    features: tuple[Decimal | None, ...]


@dataclass(frozen=True)
class PipelinePolicy:
    validation_ratio: Decimal = Decimal("0.20")
    split_mode: str = "TIME_SERIES"
    purge_size: int = 1
    random_seed: int = 42
    normalization: str = "ZSCORE"
    missing_strategy: str = "MEDIAN"
    variance_threshold: Decimal = Decimal("0.000001")
    correlation_threshold: Decimal = Decimal("0.98")
    max_features: int = 20
    learning_rate: Decimal = Decimal("0.08")
    epochs: int = 500
    l2_strength: Decimal = Decimal("0.001")
    patience: int = 30
    min_confidence: Decimal = Decimal("0.55")
    min_margin: Decimal = Decimal("0.10")
    max_entropy: Decimal = Decimal("0.85")
    hold_label: int = 0

    def __post_init__(self) -> None:
        if not (ZERO < _d(self.validation_ratio) < ONE):
            raise PipelineError("validation_ratio must be between 0 and 1")
        if self.split_mode.upper() not in {"TIME_SERIES", "STRATIFIED"}:
            raise PipelineError("unsupported split mode")
        if self.purge_size < 0:
            raise PipelineError("purge_size cannot be negative")
        if self.normalization.upper() not in {"ZSCORE", "MINMAX", "ROBUST"}:
            raise PipelineError("unsupported normalization method")
        if self.missing_strategy.upper() not in {"MEDIAN", "MEAN", "ZERO", "ERROR"}:
            raise PipelineError("unsupported missing strategy")
        if _d(self.variance_threshold) < ZERO:
            raise PipelineError("variance_threshold cannot be negative")
        if not (ZERO < _d(self.correlation_threshold) <= ONE):
            raise PipelineError("correlation_threshold must be within (0,1]")
        if self.max_features <= 0:
            raise PipelineError("max_features must be positive")
        if _d(self.learning_rate) <= ZERO or self.epochs <= 0:
            raise PipelineError("invalid training parameters")
        if _d(self.l2_strength) < ZERO or self.patience <= 0:
            raise PipelineError("invalid regularization or patience")
        for name in ("min_confidence", "min_margin", "max_entropy"):
            value = _d(getattr(self, name))
            if not (ZERO <= value <= ONE):
                raise PipelineError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class FeatureStat:
    index: int
    fill_value: Decimal
    minimum: Decimal
    maximum: Decimal
    mean: Decimal
    stddev: Decimal
    median: Decimal
    q1: Decimal
    q3: Decimal


@dataclass(frozen=True)
class PipelineModel:
    classes: tuple[int, ...]
    selected_feature_indices: tuple[int, ...]
    weights: tuple[tuple[Decimal, ...], ...]
    biases: tuple[Decimal, ...]
    feature_stats: tuple[FeatureStat, ...]
    model_hash: str


@dataclass(frozen=True)
class PredictionOutput:
    prediction_id: str
    timestamp: str
    raw_label: int
    final_label: int
    probabilities: tuple[Decimal, ...]
    confidence: Decimal
    margin: Decimal
    entropy: Decimal
    forced_hold: bool
    reason_codes: tuple[str, ...]
    prediction_hash: str


@dataclass(frozen=True)
class PipelineResult:
    version: str
    experiment_id: str
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    purged_ids: tuple[str, ...]
    selected_feature_names: tuple[str, ...]
    train_accuracy: Decimal
    validation_accuracy: Decimal
    validation_log_loss: Decimal
    model: PipelineModel
    predictions: tuple[PredictionOutput, ...]
    input_hash: str
    result_hash: str


def _normalize_rows(
    rows: Iterable[PipelineRow],
    feature_count: int | None = None,
) -> tuple[PipelineRow, ...]:
    output = []
    width = feature_count
    for row in rows:
        rid = row.row_id.strip()
        ts = row.timestamp.strip()
        if not rid or not ts:
            raise PipelineError("row_id and timestamp are required")
        if width is None:
            width = len(row.features)
        if width <= 0 or len(row.features) != width:
            raise PipelineError("inconsistent feature width")
        values = tuple(None if value is None else _d(value) for value in row.features)
        output.append(PipelineRow(rid, ts, values, int(row.label)))
    if len(output) < 6:
        raise PipelineError("at least six rows are required")
    if len({row.row_id for row in output}) != len(output):
        raise PipelineError("duplicate row IDs detected")
    if len({row.timestamp for row in output}) != len(output):
        raise PipelineError("duplicate timestamps detected")
    return tuple(output)


def _split(
    rows: tuple[PipelineRow, ...],
    policy: PipelinePolicy,
) -> tuple[tuple[PipelineRow, ...], tuple[PipelineRow, ...], tuple[PipelineRow, ...]]:
    ratio = _d(policy.validation_ratio)
    validation_count = int(
        (Decimal(len(rows)) * ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    validation_count = max(1, min(len(rows) - 2, validation_count))

    if policy.split_mode.upper() == "TIME_SERIES":
        ordered = tuple(sorted(rows, key=lambda row: row.timestamp))
        val_start = len(ordered) - validation_count
        purge_start = max(1, val_start - policy.purge_size)
        train = ordered[:purge_start]
        purged = ordered[purge_start:val_start]
        validation = ordered[val_start:]
    else:
        grouped: dict[int, list[PipelineRow]] = {}
        for row in rows:
            grouped.setdefault(row.label, []).append(row)
        rng = random.Random(policy.random_seed)
        train_list, val_list = [], []
        for label in sorted(grouped):
            group = sorted(grouped[label], key=lambda row: row.row_id)
            rng.shuffle(group)
            count = max(1, int(round(len(group) * float(ratio)))) if len(group) > 1 else 0
            count = min(count, len(group) - 1) if len(group) > 1 else 0
            val_list.extend(group[:count])
            train_list.extend(group[count:])
        rng.shuffle(train_list)
        rng.shuffle(val_list)
        train, validation, purged = tuple(train_list), tuple(val_list), ()

    if not train or not validation:
        raise PipelineError("split produced an empty partition")
    if {row.row_id for row in train} & {row.row_id for row in validation}:
        raise PipelineError("train/validation leakage detected")
    return tuple(train), tuple(validation), tuple(purged)


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _percentile(values: list[Decimal], fraction: Decimal) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = float(fraction) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = Decimal(str(rank - low))
    return ordered[low] * (ONE - weight) + ordered[high] * weight


def _fit_stats(
    rows: tuple[PipelineRow, ...],
    policy: PipelinePolicy,
) -> tuple[FeatureStat, ...]:
    width = len(rows[0].features)
    stats = []
    for index in range(width):
        observed = [row.features[index] for row in rows if row.features[index] is not None]
        observed = [_d(value) for value in observed]
        if not observed:
            raise PipelineError(f"feature {index} contains only missing values")
        avg = sum(observed, ZERO) / Decimal(len(observed))
        med = _median(observed)
        q1 = _percentile(observed, Decimal("0.25"))
        q3 = _percentile(observed, Decimal("0.75"))
        variance = sum((value - avg) ** 2 for value in observed) / Decimal(len(observed))
        stddev = _d(sqrt(float(variance)))

        strategy = policy.missing_strategy.upper()
        if strategy == "MEDIAN":
            fill = med
        elif strategy == "MEAN":
            fill = avg
        elif strategy == "ZERO":
            fill = ZERO
        else:
            if any(row.features[index] is None for row in rows):
                raise PipelineError("missing value encountered with ERROR strategy")
            fill = med

        stats.append(FeatureStat(
            index=index,
            fill_value=_q(fill),
            minimum=_q(min(observed)),
            maximum=_q(max(observed)),
            mean=_q(avg),
            stddev=_q(stddev),
            median=_q(med),
            q1=_q(q1),
            q3=_q(q3),
        ))
    return tuple(stats)


def _transform_value(value: Decimal | None, stat: FeatureStat, method: str) -> Decimal:
    raw = stat.fill_value if value is None else _d(value)
    if method == "ZSCORE":
        return ZERO if stat.stddev == ZERO else _q((raw - stat.mean) / stat.stddev)
    if method == "MINMAX":
        span = stat.maximum - stat.minimum
        return ZERO if span == ZERO else _q((raw - stat.minimum) / span)
    iqr = stat.q3 - stat.q1
    return ZERO if iqr == ZERO else _q((raw - stat.median) / iqr)


def _transform_rows(
    rows: Sequence[PipelineRow],
    stats: tuple[FeatureStat, ...],
    method: str,
) -> tuple[tuple[Decimal, ...], ...]:
    output = []
    for row in rows:
        if len(row.features) != len(stats):
            raise PipelineError("transform width mismatch")
        output.append(tuple(
            _transform_value(row.features[index], stats[index], method)
            for index in range(len(stats))
        ))
    return tuple(output)


def _variance(values: list[Decimal]) -> Decimal:
    avg = sum(values, ZERO) / Decimal(len(values))
    return sum((value - avg) ** 2 for value in values) / Decimal(len(values))


def _pearson(left: list[Decimal], right: list[Decimal]) -> Decimal:
    left_avg = sum(left, ZERO) / Decimal(len(left))
    right_avg = sum(right, ZERO) / Decimal(len(right))
    numerator = sum((a-left_avg)*(b-right_avg) for a,b in zip(left,right))
    left_ss = sum((a-left_avg)**2 for a in left)
    right_ss = sum((b-right_avg)**2 for b in right)
    if left_ss == ZERO or right_ss == ZERO:
        return ZERO
    return _d(numerator / _d(sqrt(float(left_ss * right_ss))))


def _select_features(
    matrix: tuple[tuple[Decimal, ...], ...],
    labels: tuple[int, ...],
    policy: PipelinePolicy,
) -> tuple[int, ...]:
    width = len(matrix[0])
    columns = [[row[index] for row in matrix] for index in range(width)]
    keep = [
        index for index in range(width)
        if _variance(columns[index]) >= _d(policy.variance_threshold)
    ]
    if not keep:
        raise PipelineError("all features were removed by variance threshold")

    label_values = [_d(label) for label in labels]
    ranked = sorted(
        keep,
        key=lambda index: (abs(_pearson(columns[index], label_values)), -index),
        reverse=True,
    )

    selected = []
    for index in ranked:
        if any(
            abs(_pearson(columns[index], columns[chosen]))
            >= _d(policy.correlation_threshold)
            for chosen in selected
        ):
            continue
        selected.append(index)
        if len(selected) >= policy.max_features:
            break

    if not selected:
        raise PipelineError("feature selection produced no features")
    return tuple(selected)


def _softmax(logits: list[float]) -> list[float]:
    maximum = max(logits)
    values = [exp(value - maximum) for value in logits]
    total = sum(values)
    return [value / total for value in values]


def _predict_raw(
    features: tuple[Decimal, ...],
    weights: list[list[float]],
    biases: list[float],
) -> list[float]:
    logits = [
        sum(float(value) * weight for value, weight in zip(features, class_weights))
        + biases[class_index]
        for class_index, class_weights in enumerate(weights)
    ]
    return _softmax(logits)


def _train(
    train_x: tuple[tuple[Decimal, ...], ...],
    train_y: tuple[int, ...],
    validation_x: tuple[tuple[Decimal, ...], ...],
    validation_y: tuple[int, ...],
    policy: PipelinePolicy,
) -> tuple[
    tuple[int, ...],
    tuple[tuple[Decimal, ...], ...],
    tuple[Decimal, ...],
    Decimal,
    Decimal,
    Decimal,
]:
    classes = tuple(sorted(set(train_y)))
    if len(classes) < 2:
        raise PipelineError("at least two training classes are required")
    if not set(validation_y).issubset(set(classes)):
        raise PipelineError("validation contains unseen class")

    class_index = {label:index for index,label in enumerate(classes)}
    width = len(train_x[0])
    rng = random.Random(policy.random_seed)
    weights = [[rng.uniform(-0.01,0.01) for _ in range(width)] for _ in classes]
    biases = [0.0 for _ in classes]
    lr = float(policy.learning_rate)
    l2 = float(policy.l2_strength)
    counts = {label:train_y.count(label) for label in classes}
    sample_weights = {
        label: len(train_y)/(len(classes)*counts[label])
        for label in classes
    }

    best_loss = float("inf")
    best_weights = [row[:] for row in weights]
    best_biases = biases[:]
    no_improvement = 0

    for _epoch in range(policy.epochs):
        grad_w = [[0.0]*width for _ in classes]
        grad_b = [0.0]*len(classes)
        total_weight = 0.0

        for features,label in zip(train_x,train_y):
            probs = _predict_raw(features,weights,biases)
            target = class_index[label]
            sw = sample_weights[label]
            total_weight += sw
            for c in range(len(classes)):
                error = (probs[c] - (1.0 if c == target else 0.0))*sw
                grad_b[c] += error
                for j,value in enumerate(features):
                    grad_w[c][j] += error*float(value)

        for c in range(len(classes)):
            biases[c] -= lr*grad_b[c]/total_weight
            for j in range(width):
                weights[c][j] -= lr*(grad_w[c][j]/total_weight + l2*weights[c][j])

        loss = 0.0
        for features,label in zip(train_x,train_y):
            probs = _predict_raw(features,weights,biases)
            loss -= log(max(probs[class_index[label]],1e-15))
        loss /= len(train_x)
        loss += 0.5*l2*sum(value*value for row in weights for value in row)

        if best_loss-loss > 1e-7:
            best_loss = loss
            best_weights = [row[:] for row in weights]
            best_biases = biases[:]
            no_improvement = 0
        else:
            no_improvement += 1
            if no_improvement >= policy.patience:
                break

    def predictions(x_rows):
        return tuple(
            classes[max(range(len(classes)),key=lambda c:_predict_raw(row,best_weights,best_biases)[c])]
            for row in x_rows
        )

    train_pred = predictions(train_x)
    val_pred = predictions(validation_x)
    train_acc = Decimal(sum(a==b for a,b in zip(train_y,train_pred)))/Decimal(len(train_y))
    val_acc = Decimal(sum(a==b for a,b in zip(validation_y,val_pred)))/Decimal(len(validation_y))

    val_loss = 0.0
    for features,label in zip(validation_x,validation_y):
        probs = _predict_raw(features,best_weights,best_biases)
        val_loss -= log(max(probs[class_index[label]],1e-15))
    val_loss /= len(validation_x)

    return (
        classes,
        tuple(tuple(_q(value) for value in row) for row in best_weights),
        tuple(_q(value) for value in best_biases),
        _q(train_acc),
        _q(val_acc),
        _q(val_loss),
    )


def _model_payload(model: PipelineModel, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "classes": list(model.classes),
        "selected_feature_indices": list(model.selected_feature_indices),
        "weights": [[str(value) for value in row] for row in model.weights],
        "biases": [str(value) for value in model.biases],
        "feature_stats": [
            {
                "index": stat.index,
                "fill_value": str(stat.fill_value),
                "minimum": str(stat.minimum),
                "maximum": str(stat.maximum),
                "mean": str(stat.mean),
                "stddev": str(stat.stddev),
                "median": str(stat.median),
                "q1": str(stat.q1),
                "q3": str(stat.q3),
            }
            for stat in model.feature_stats
        ],
    }
    if include_hash:
        payload["model_hash"] = model.model_hash
    return payload


def _prediction_payload(prediction: PredictionOutput, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "prediction_id": prediction.prediction_id,
        "timestamp": prediction.timestamp,
        "raw_label": prediction.raw_label,
        "final_label": prediction.final_label,
        "probabilities": [str(value) for value in prediction.probabilities],
        "confidence": str(prediction.confidence),
        "margin": str(prediction.margin),
        "entropy": str(prediction.entropy),
        "forced_hold": prediction.forced_hold,
        "reason_codes": list(prediction.reason_codes),
    }
    if include_hash:
        payload["prediction_hash"] = prediction.prediction_hash
    return payload


def _result_payload(result: PipelineResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "experiment_id": result.experiment_id,
        "train_ids": list(result.train_ids),
        "validation_ids": list(result.validation_ids),
        "purged_ids": list(result.purged_ids),
        "selected_feature_names": list(result.selected_feature_names),
        "train_accuracy": str(result.train_accuracy),
        "validation_accuracy": str(result.validation_accuracy),
        "validation_log_loss": str(result.validation_log_loss),
        "model": _model_payload(result.model, include_hash=True),
        "predictions": [_prediction_payload(item, include_hash=True) for item in result.predictions],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _predict_request(
    request: PredictionRequest,
    model: PipelineModel,
    feature_names: tuple[str, ...],
    policy: PipelinePolicy,
) -> PredictionOutput:
    if not request.prediction_id.strip() or not request.timestamp.strip():
        raise PipelineError("prediction ID and timestamp are required")
    if len(request.features) != len(feature_names):
        raise PipelineError("prediction feature width mismatch")

    full = tuple(
        _transform_value(request.features[index], model.feature_stats[index], policy.normalization.upper())
        for index in range(len(feature_names))
    )
    selected = tuple(full[index] for index in model.selected_feature_indices)
    probabilities_float = _predict_raw(
        selected,
        [[float(value) for value in row] for row in model.weights],
        [float(value) for value in model.biases],
    )
    probabilities = tuple(_q(value) for value in probabilities_float)
    difference = Decimal("1.000000") - sum(probabilities, ZERO)
    probabilities = probabilities[:-1] + (probabilities[-1] + difference,)

    ranked = sorted(
        range(len(model.classes)),
        key=lambda index:(probabilities[index],-index),
        reverse=True,
    )
    raw_label = model.classes[ranked[0]]
    confidence = probabilities[ranked[0]]
    margin = _q(probabilities[ranked[0]]-probabilities[ranked[1]])

    entropy_float = -sum(
        float(p)*log(float(p))
        for p in probabilities if p>ZERO
    )/log(len(probabilities))
    entropy = _q(entropy_float)

    reasons = []
    if confidence < _d(policy.min_confidence):
        reasons.append("LOW_CONFIDENCE")
    if margin < _d(policy.min_margin):
        reasons.append("LOW_MARGIN")
    if entropy > _d(policy.max_entropy):
        reasons.append("HIGH_ENTROPY")

    forced = bool(reasons)
    final_label = policy.hold_label if forced else raw_label
    prediction = PredictionOutput(
        prediction_id=request.prediction_id.strip(),
        timestamp=request.timestamp.strip(),
        raw_label=raw_label,
        final_label=final_label,
        probabilities=probabilities,
        confidence=confidence,
        margin=margin,
        entropy=entropy,
        forced_hold=forced,
        reason_codes=tuple(sorted(reasons)),
        prediction_hash="",
    )
    return replace(prediction,prediction_hash=_hash(_prediction_payload(prediction)))


def run_pipeline(
    rows: Iterable[PipelineRow],
    feature_names: Sequence[str],
    prediction_requests: Iterable[PredictionRequest],
    policy: PipelinePolicy | None = None,
) -> PipelineResult:
    selected_policy = policy or PipelinePolicy()
    names = tuple(name.strip() for name in feature_names)
    if not names or any(not name for name in names):
        raise PipelineError("feature names are required")
    if len(names) != len(set(names)):
        raise PipelineError("duplicate feature names detected")

    data = _normalize_rows(rows, len(names))
    train, validation, purged = _split(data, selected_policy)
    stats = _fit_stats(train, selected_policy)

    train_full = _transform_rows(train, stats, selected_policy.normalization.upper())
    validation_full = _transform_rows(validation, stats, selected_policy.normalization.upper())
    train_y = tuple(row.label for row in train)
    validation_y = tuple(row.label for row in validation)
    selected_indices = _select_features(train_full, train_y, selected_policy)

    train_x = tuple(tuple(row[index] for index in selected_indices) for row in train_full)
    validation_x = tuple(tuple(row[index] for index in selected_indices) for row in validation_full)

    classes, weights, biases, train_acc, val_acc, val_loss = _train(
        train_x, train_y, validation_x, validation_y, selected_policy
    )

    if selected_policy.hold_label not in classes:
        raise PipelineError("configured HOLD label is absent from trained classes")

    model = PipelineModel(
        classes=classes,
        selected_feature_indices=selected_indices,
        weights=weights,
        biases=biases,
        feature_stats=stats,
        model_hash="",
    )
    model = replace(model,model_hash=_hash(_model_payload(model)))

    requests = tuple(prediction_requests)
    if len({request.prediction_id for request in requests}) != len(requests):
        raise PipelineError("duplicate prediction IDs detected")
    predictions = tuple(
        _predict_request(request,model,names,selected_policy)
        for request in requests
    )

    input_hash = _hash({
        "rows": [
            {
                "row_id":row.row_id,
                "timestamp":row.timestamp,
                "features":[None if value is None else str(value) for value in row.features],
                "label":row.label,
            }
            for row in data
        ],
        "feature_names":list(names),
        "requests":[
            {
                "prediction_id":request.prediction_id,
                "timestamp":request.timestamp,
                "features":[None if value is None else str(value) for value in request.features],
            }
            for request in requests
        ],
        "policy":{key:str(value) for key,value in selected_policy.__dict__.items()},
    })

    experiment_id = f"EXP-{input_hash[:16].upper()}"
    result = PipelineResult(
        version=VERSION,
        experiment_id=experiment_id,
        train_ids=tuple(row.row_id for row in train),
        validation_ids=tuple(row.row_id for row in validation),
        purged_ids=tuple(row.row_id for row in purged),
        selected_feature_names=tuple(names[index] for index in selected_indices),
        train_accuracy=train_acc,
        validation_accuracy=val_acc,
        validation_log_loss=val_loss,
        model=model,
        predictions=predictions,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result,result_hash=_hash(_result_payload(result)))


def verify_result(result: PipelineResult) -> bool:
    if result.version != VERSION:
        raise PipelineError("unsupported pipeline version")
    if not result.experiment_id.startswith("EXP-"):
        raise PipelineError("invalid experiment ID")
    if set(result.train_ids)&set(result.validation_ids):
        raise PipelineError("train/validation leakage detected")
    if not result.selected_feature_names:
        raise PipelineError("no selected features")
    clean_model = replace(result.model,model_hash="")
    if result.model.model_hash != _hash(_model_payload(clean_model)):
        raise PipelineError("model hash mismatch")
    for prediction in result.predictions:
        clean_prediction = replace(prediction,prediction_hash="")
        if prediction.prediction_hash != _hash(_prediction_payload(clean_prediction)):
            raise PipelineError("prediction hash mismatch")
    clean = replace(result,result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise PipelineError("pipeline result hash mismatch")
    return True


def save_result(result: PipelineResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result,include_hash=True),indent=2,sort_keys=True),
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
