from __future__ import annotations

"""
V28.1 Offline Experiment Manager

Features:
- deterministic experiment IDs
- hyperparameter and metric registry
- experiment ranking
- best-model tracking
- previous-run comparison
- duplicate experiment blocking
- immutable experiment records
- SHA-256 record and registry integrity
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
import json

VERSION = "28.1"
ZERO = Decimal("0")
SIX = Decimal("0.000001")


class ExperimentError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ExperimentError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ExperimentError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExperimentMetrics:
    accuracy: Decimal
    precision: Decimal
    recall: Decimal
    f1: Decimal
    validation_loss: Decimal
    sharpe: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    pipeline_version: str
    model_hash: str
    dataset_hash: str
    feature_names: tuple[str, ...]
    hyperparameters: tuple[tuple[str, str], ...]
    metrics: ExperimentMetrics
    score: Decimal
    record_hash: str


@dataclass(frozen=True)
class ExperimentComparison:
    current_id: str
    previous_id: str
    score_delta: Decimal
    accuracy_delta: Decimal
    f1_delta: Decimal
    loss_delta: Decimal
    improved: bool


@dataclass(frozen=True)
class ExperimentRegistry:
    version: str
    experiments: tuple[ExperimentRecord, ...]
    best_experiment_id: str
    ranking: tuple[str, ...]
    registry_hash: str


def _metrics_payload(metrics: ExperimentMetrics) -> dict[str, str]:
    return {
        "accuracy": str(metrics.accuracy),
        "precision": str(metrics.precision),
        "recall": str(metrics.recall),
        "f1": str(metrics.f1),
        "validation_loss": str(metrics.validation_loss),
        "sharpe": str(metrics.sharpe),
        "total_return_pct": str(metrics.total_return_pct),
        "max_drawdown_pct": str(metrics.max_drawdown_pct),
    }


def _record_payload(record: ExperimentRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "experiment_id": record.experiment_id,
        "pipeline_version": record.pipeline_version,
        "model_hash": record.model_hash,
        "dataset_hash": record.dataset_hash,
        "feature_names": list(record.feature_names),
        "hyperparameters": dict(record.hyperparameters),
        "metrics": _metrics_payload(record.metrics),
        "score": str(record.score),
    }
    if include_hash:
        payload["record_hash"] = record.record_hash
    return payload


def _registry_payload(registry: ExperimentRegistry, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": registry.version,
        "experiments": [
            _record_payload(record, include_hash=True)
            for record in registry.experiments
        ],
        "best_experiment_id": registry.best_experiment_id,
        "ranking": list(registry.ranking),
    }
    if include_hash:
        payload["registry_hash"] = registry.registry_hash
    return payload


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ExperimentError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _normalize_metrics(metrics: ExperimentMetrics) -> ExperimentMetrics:
    accuracy = _q(metrics.accuracy)
    precision = _q(metrics.precision)
    recall = _q(metrics.recall)
    f1 = _q(metrics.f1)
    loss = _q(metrics.validation_loss)
    sharpe = _q(metrics.sharpe)
    total_return = _q(metrics.total_return_pct)
    max_drawdown = _q(metrics.max_drawdown_pct)

    for name, value in (
        ("accuracy", accuracy),
        ("precision", precision),
        ("recall", recall),
        ("f1", f1),
    ):
        if value < ZERO or value > Decimal("1"):
            raise ExperimentError(f"{name} must be between 0 and 1")
    if loss < ZERO:
        raise ExperimentError("validation_loss cannot be negative")
    if max_drawdown > ZERO:
        raise ExperimentError("max_drawdown_pct must be zero or negative")

    return ExperimentMetrics(
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        validation_loss=loss,
        sharpe=sharpe,
        total_return_pct=total_return,
        max_drawdown_pct=max_drawdown,
    )


def _score(metrics: ExperimentMetrics) -> Decimal:
    """
    Weighted offline research score.
    Higher is better.
    """
    return _q(
        metrics.accuracy * Decimal("0.20")
        + metrics.precision * Decimal("0.10")
        + metrics.recall * Decimal("0.10")
        + metrics.f1 * Decimal("0.20")
        + max(metrics.sharpe, Decimal("-5")) / Decimal("10") * Decimal("0.15")
        + metrics.total_return_pct / Decimal("100") * Decimal("0.15")
        + metrics.max_drawdown_pct / Decimal("100") * Decimal("0.05")
        - metrics.validation_loss * Decimal("0.05")
    )


def create_experiment(
    *,
    pipeline_version: str,
    model_hash: str,
    dataset_hash: str,
    feature_names: Iterable[str],
    hyperparameters: Mapping[str, Any],
    metrics: ExperimentMetrics,
) -> ExperimentRecord:
    version = pipeline_version.strip()
    if not version:
        raise ExperimentError("pipeline_version is required")

    model_digest = _validate_sha256(model_hash, "model_hash")
    dataset_digest = _validate_sha256(dataset_hash, "dataset_hash")

    features = tuple(name.strip() for name in feature_names)
    if not features or any(not name for name in features):
        raise ExperimentError("feature names are required")
    if len(features) != len(set(features)):
        raise ExperimentError("duplicate feature names detected")

    params = tuple(sorted(
        (str(key).strip(), str(value))
        for key, value in hyperparameters.items()
    ))
    if not params or any(not key for key, _ in params):
        raise ExperimentError("hyperparameters are required")

    normalized_metrics = _normalize_metrics(metrics)
    score = _score(normalized_metrics)

    identity_payload = {
        "pipeline_version": version,
        "model_hash": model_digest,
        "dataset_hash": dataset_digest,
        "feature_names": list(features),
        "hyperparameters": dict(params),
        "metrics": _metrics_payload(normalized_metrics),
    }
    experiment_id = f"EXP-{_hash(identity_payload)[:16].upper()}"

    record = ExperimentRecord(
        experiment_id=experiment_id,
        pipeline_version=version,
        model_hash=model_digest,
        dataset_hash=dataset_digest,
        feature_names=features,
        hyperparameters=params,
        metrics=normalized_metrics,
        score=score,
        record_hash="",
    )
    return replace(record, record_hash=_hash(_record_payload(record)))


def verify_record(record: ExperimentRecord) -> bool:
    if not record.experiment_id.startswith("EXP-"):
        raise ExperimentError("invalid experiment ID")
    _validate_sha256(record.model_hash, "model_hash")
    _validate_sha256(record.dataset_hash, "dataset_hash")
    _normalize_metrics(record.metrics)

    expected_score = _score(record.metrics)
    if record.score != expected_score:
        raise ExperimentError("experiment score mismatch")

    clean = replace(record, record_hash="")
    if record.record_hash != _hash(_record_payload(clean)):
        raise ExperimentError("experiment record hash mismatch")
    return True


def create_registry(records: Iterable[ExperimentRecord]) -> ExperimentRegistry:
    experiments = tuple(sorted(records, key=lambda item: item.experiment_id))
    if not experiments:
        raise ExperimentError("registry requires at least one experiment")
    if len({record.experiment_id for record in experiments}) != len(experiments):
        raise ExperimentError("duplicate experiment IDs detected")

    for record in experiments:
        verify_record(record)

    ranked = tuple(
        record.experiment_id
        for record in sorted(
            experiments,
            key=lambda item: (
                item.score,
                item.metrics.accuracy,
                item.metrics.f1,
                -item.metrics.validation_loss,
                item.experiment_id,
            ),
            reverse=True,
        )
    )

    registry = ExperimentRegistry(
        version=VERSION,
        experiments=experiments,
        best_experiment_id=ranked[0],
        ranking=ranked,
        registry_hash="",
    )
    return replace(registry, registry_hash=_hash(_registry_payload(registry)))


def add_experiment(
    registry: ExperimentRegistry,
    record: ExperimentRecord,
) -> ExperimentRegistry:
    verify_registry(registry)
    verify_record(record)
    if record.experiment_id in {item.experiment_id for item in registry.experiments}:
        raise ExperimentError("duplicate experiment ID detected")
    return create_registry(registry.experiments + (record,))


def compare_experiments(
    current: ExperimentRecord,
    previous: ExperimentRecord,
) -> ExperimentComparison:
    verify_record(current)
    verify_record(previous)
    return ExperimentComparison(
        current_id=current.experiment_id,
        previous_id=previous.experiment_id,
        score_delta=_q(current.score - previous.score),
        accuracy_delta=_q(current.metrics.accuracy - previous.metrics.accuracy),
        f1_delta=_q(current.metrics.f1 - previous.metrics.f1),
        loss_delta=_q(current.metrics.validation_loss - previous.metrics.validation_loss),
        improved=current.score > previous.score,
    )


def verify_registry(registry: ExperimentRegistry) -> bool:
    if registry.version != VERSION:
        raise ExperimentError("unsupported registry version")
    if not registry.experiments:
        raise ExperimentError("registry cannot be empty")
    if len({record.experiment_id for record in registry.experiments}) != len(registry.experiments):
        raise ExperimentError("duplicate experiment IDs detected")

    for record in registry.experiments:
        verify_record(record)

    expected_ranking = tuple(
        record.experiment_id
        for record in sorted(
            registry.experiments,
            key=lambda item: (
                item.score,
                item.metrics.accuracy,
                item.metrics.f1,
                -item.metrics.validation_loss,
                item.experiment_id,
            ),
            reverse=True,
        )
    )
    if registry.ranking != expected_ranking:
        raise ExperimentError("registry ranking mismatch")
    if registry.best_experiment_id != expected_ranking[0]:
        raise ExperimentError("best experiment mismatch")

    clean = replace(registry, registry_hash="")
    if registry.registry_hash != _hash(_registry_payload(clean)):
        raise ExperimentError("registry hash mismatch")
    return True


def save_registry(registry: ExperimentRegistry, path: str | Path) -> Path:
    verify_registry(registry)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_registry_payload(registry, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_registry(path: str | Path) -> ExperimentRegistry:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = []
    for item in payload["experiments"]:
        metric_data = item["metrics"]
        metrics = ExperimentMetrics(
            accuracy=_d(metric_data["accuracy"]),
            precision=_d(metric_data["precision"]),
            recall=_d(metric_data["recall"]),
            f1=_d(metric_data["f1"]),
            validation_loss=_d(metric_data["validation_loss"]),
            sharpe=_d(metric_data["sharpe"]),
            total_return_pct=_d(metric_data["total_return_pct"]),
            max_drawdown_pct=_d(metric_data["max_drawdown_pct"]),
        )
        records.append(ExperimentRecord(
            experiment_id=item["experiment_id"],
            pipeline_version=item["pipeline_version"],
            model_hash=item["model_hash"],
            dataset_hash=item["dataset_hash"],
            feature_names=tuple(item["feature_names"]),
            hyperparameters=tuple(sorted(item["hyperparameters"].items())),
            metrics=metrics,
            score=_d(item["score"]),
            record_hash=item["record_hash"],
        ))

    registry = ExperimentRegistry(
        version=payload["version"],
        experiments=tuple(records),
        best_experiment_id=payload["best_experiment_id"],
        ranking=tuple(payload["ranking"]),
        registry_hash=payload["registry_hash"],
    )
    verify_registry(registry)
    return registry


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
