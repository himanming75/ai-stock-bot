from __future__ import annotations

"""
V27.7 Offline Prediction & Confidence Engine

Consumes a trained V27.6 model artifact and produces deterministic,
auditable SELL / HOLD / BUY decisions with confidence controls.

Features:
- class probability validation
- top-class prediction
- confidence score
- probability margin
- normalized entropy uncertainty
- configurable low-confidence HOLD override
- feature schema and model-hash binding
- single and batch prediction
- prediction history
- JSON and CSV export
- SHA-256 integrity verification
- tamper detection

Safety boundary:
- no network access
- no market/account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import log
from pathlib import Path
from typing import Any, Iterable, Sequence
import csv
import json

VERSION = "27.7"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class PredictionError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise PredictionError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise PredictionError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PredictionPolicy:
    min_confidence: Decimal = Decimal("0.55")
    min_margin: Decimal = Decimal("0.10")
    max_entropy: Decimal = Decimal("0.85")
    force_hold_on_low_confidence: bool = True
    hold_label: int = 0

    def __post_init__(self) -> None:
        for name in ("min_confidence", "min_margin", "max_entropy"):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise PredictionError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class ModelBinding:
    model_version: str
    model_hash: str
    feature_names: tuple[str, ...]
    classes: tuple[int, ...]
    binding_hash: str


@dataclass(frozen=True)
class PredictionInput:
    prediction_id: str
    timestamp: str
    features: tuple[Decimal, ...]


@dataclass(frozen=True)
class ClassProbability:
    label: int
    probability: Decimal


@dataclass(frozen=True)
class PredictionRecord:
    version: str
    prediction_id: str
    timestamp: str
    raw_label: int
    final_label: int
    probabilities: tuple[ClassProbability, ...]
    confidence: Decimal
    probability_margin: Decimal
    normalized_entropy: Decimal
    forced_hold: bool
    reason_codes: tuple[str, ...]
    model_hash: str
    binding_hash: str
    input_hash: str
    prediction_hash: str


@dataclass(frozen=True)
class PredictionHistory:
    version: str
    records: tuple[PredictionRecord, ...]
    history_hash: str


def _binding_payload(binding: ModelBinding, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "model_version": binding.model_version,
        "model_hash": binding.model_hash,
        "feature_names": list(binding.feature_names),
        "classes": list(binding.classes),
    }
    if include_hash:
        payload["binding_hash"] = binding.binding_hash
    return payload


def _probability_payload(item: ClassProbability) -> dict[str, Any]:
    return {"label": item.label, "probability": str(item.probability)}


def _record_payload(record: PredictionRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": record.version,
        "prediction_id": record.prediction_id,
        "timestamp": record.timestamp,
        "raw_label": record.raw_label,
        "final_label": record.final_label,
        "probabilities": [_probability_payload(item) for item in record.probabilities],
        "confidence": str(record.confidence),
        "probability_margin": str(record.probability_margin),
        "normalized_entropy": str(record.normalized_entropy),
        "forced_hold": record.forced_hold,
        "reason_codes": list(record.reason_codes),
        "model_hash": record.model_hash,
        "binding_hash": record.binding_hash,
        "input_hash": record.input_hash,
    }
    if include_hash:
        payload["prediction_hash"] = record.prediction_hash
    return payload


def _history_payload(history: PredictionHistory, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": history.version,
        "records": [_record_payload(record, include_hash=True) for record in history.records],
    }
    if include_hash:
        payload["history_hash"] = history.history_hash
    return payload


def create_binding(
    *,
    model_version: str,
    model_hash: str,
    feature_names: Sequence[str],
    classes: Sequence[int],
) -> ModelBinding:
    version = model_version.strip()
    digest = model_hash.strip()
    names = tuple(name.strip() for name in feature_names)
    class_values = tuple(int(value) for value in classes)

    if not version:
        raise PredictionError("model_version is required")
    if len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
        raise PredictionError("model_hash must be a SHA-256 hex digest")
    if not names or any(not name for name in names):
        raise PredictionError("feature names are required")
    if len(names) != len(set(names)):
        raise PredictionError("duplicate feature names detected")
    if len(class_values) < 2 or len(class_values) != len(set(class_values)):
        raise PredictionError("invalid class list")

    binding = ModelBinding(
        model_version=version,
        model_hash=digest.lower(),
        feature_names=names,
        classes=class_values,
        binding_hash="",
    )
    return replace(binding, binding_hash=_hash(_binding_payload(binding)))


def verify_binding(binding: ModelBinding) -> bool:
    if not binding.feature_names or len(binding.feature_names) != len(set(binding.feature_names)):
        raise PredictionError("invalid binding feature schema")
    if len(binding.classes) < 2 or len(binding.classes) != len(set(binding.classes)):
        raise PredictionError("invalid binding classes")
    clean = replace(binding, binding_hash="")
    if binding.binding_hash != _hash(_binding_payload(clean)):
        raise PredictionError("binding hash mismatch")
    return True


def _normalize_probabilities(
    classes: tuple[int, ...],
    probabilities: Iterable[Any],
) -> tuple[ClassProbability, ...]:
    values = tuple(_q(value) for value in probabilities)
    if len(values) != len(classes):
        raise PredictionError("probability count does not match class count")
    if any(value < ZERO or value > ONE for value in values):
        raise PredictionError("probabilities must be between 0 and 1")
    total = sum(values, ZERO)
    if abs(total - ONE) > Decimal("0.000010"):
        raise PredictionError("probabilities must sum to one")
    difference = Decimal("1.000000") - total
    values = values[:-1] + (values[-1] + difference,)
    return tuple(
        ClassProbability(label, probability)
        for label, probability in zip(classes, values)
    )


def _entropy(probabilities: tuple[ClassProbability, ...]) -> Decimal:
    count = len(probabilities)
    if count <= 1:
        return ZERO
    entropy = 0.0
    for item in probabilities:
        p = float(item.probability)
        if p > 0:
            entropy -= p * log(p)
    maximum = log(count)
    return _q(entropy / maximum if maximum > 0 else 0)


def generate_prediction(
    item: PredictionInput,
    *,
    binding: ModelBinding,
    probabilities: Iterable[Any],
    policy: PredictionPolicy | None = None,
) -> PredictionRecord:
    verify_binding(binding)
    selected = policy or PredictionPolicy()

    prediction_id = item.prediction_id.strip()
    timestamp = item.timestamp.strip()
    features = tuple(_q(value) for value in item.features)

    if not prediction_id or not timestamp:
        raise PredictionError("prediction_id and timestamp are required")
    if len(features) != len(binding.feature_names):
        raise PredictionError("feature width does not match binding schema")
    if selected.hold_label not in binding.classes:
        raise PredictionError("hold label is absent from model classes")

    probability_rows = _normalize_probabilities(binding.classes, probabilities)
    ranked = sorted(
        probability_rows,
        key=lambda row: (row.probability, -binding.classes.index(row.label)),
        reverse=True,
    )

    raw_label = ranked[0].label
    confidence = ranked[0].probability
    margin = _q(ranked[0].probability - ranked[1].probability)
    entropy = _entropy(probability_rows)

    reasons = []
    if confidence < _d(selected.min_confidence):
        reasons.append("LOW_CONFIDENCE")
    if margin < _d(selected.min_margin):
        reasons.append("LOW_MARGIN")
    if entropy > _d(selected.max_entropy):
        reasons.append("HIGH_ENTROPY")

    forced_hold = bool(reasons) and selected.force_hold_on_low_confidence
    final_label = selected.hold_label if forced_hold else raw_label

    input_hash = _hash({
        "prediction_id": prediction_id,
        "timestamp": timestamp,
        "features": [str(value) for value in features],
        "binding_hash": binding.binding_hash,
    })

    record = PredictionRecord(
        version=VERSION,
        prediction_id=prediction_id,
        timestamp=timestamp,
        raw_label=raw_label,
        final_label=final_label,
        probabilities=probability_rows,
        confidence=confidence,
        probability_margin=margin,
        normalized_entropy=entropy,
        forced_hold=forced_hold,
        reason_codes=tuple(sorted(reasons)),
        model_hash=binding.model_hash,
        binding_hash=binding.binding_hash,
        input_hash=input_hash,
        prediction_hash="",
    )
    return replace(record, prediction_hash=_hash(_record_payload(record)))


def generate_batch(
    items: Iterable[PredictionInput],
    *,
    binding: ModelBinding,
    probability_rows: Iterable[Iterable[Any]],
    policy: PredictionPolicy | None = None,
) -> PredictionHistory:
    inputs = tuple(items)
    probabilities = tuple(tuple(row) for row in probability_rows)
    if len(inputs) != len(probabilities):
        raise PredictionError("batch input and probability counts differ")
    if not inputs:
        raise PredictionError("batch cannot be empty")
    if len({item.prediction_id for item in inputs}) != len(inputs):
        raise PredictionError("duplicate prediction IDs detected")

    records = tuple(
        generate_prediction(
            item,
            binding=binding,
            probabilities=row,
            policy=policy,
        )
        for item, row in zip(inputs, probabilities)
    )
    history = PredictionHistory(VERSION, records, "")
    return replace(history, history_hash=_hash(_history_payload(history)))


def verify_record(record: PredictionRecord) -> bool:
    if record.version != VERSION:
        raise PredictionError("unsupported prediction version")
    if record.raw_label not in {item.label for item in record.probabilities}:
        raise PredictionError("raw label is absent from probabilities")
    if record.confidence != max(item.probability for item in record.probabilities):
        raise PredictionError("confidence does not match maximum probability")
    if record.forced_hold and not record.reason_codes:
        raise PredictionError("forced HOLD requires reason codes")
    clean = replace(record, prediction_hash="")
    if record.prediction_hash != _hash(_record_payload(clean)):
        raise PredictionError("prediction hash mismatch")
    return True


def verify_history(history: PredictionHistory) -> bool:
    if history.version != VERSION:
        raise PredictionError("unsupported history version")
    if not history.records:
        raise PredictionError("prediction history cannot be empty")
    if len({record.prediction_id for record in history.records}) != len(history.records):
        raise PredictionError("duplicate prediction IDs detected")
    for record in history.records:
        verify_record(record)
    clean = replace(history, history_hash="")
    if history.history_hash != _hash(_history_payload(clean)):
        raise PredictionError("history hash mismatch")
    return True


def save_history(history: PredictionHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_history_payload(history, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_history(path: str | Path) -> PredictionHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = []
    for item in payload["records"]:
        records.append(PredictionRecord(
            version=item["version"],
            prediction_id=item["prediction_id"],
            timestamp=item["timestamp"],
            raw_label=int(item["raw_label"]),
            final_label=int(item["final_label"]),
            probabilities=tuple(
                ClassProbability(int(row["label"]), _d(row["probability"]))
                for row in item["probabilities"]
            ),
            confidence=_d(item["confidence"]),
            probability_margin=_d(item["probability_margin"]),
            normalized_entropy=_d(item["normalized_entropy"]),
            forced_hold=bool(item["forced_hold"]),
            reason_codes=tuple(item["reason_codes"]),
            model_hash=item["model_hash"],
            binding_hash=item["binding_hash"],
            input_hash=item["input_hash"],
            prediction_hash=item["prediction_hash"],
        ))
    history = PredictionHistory(
        version=payload["version"],
        records=tuple(records),
        history_hash=payload["history_hash"],
    )
    verify_history(history)
    return history


def export_csv(history: PredictionHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "prediction_id", "timestamp", "raw_label", "final_label",
            "confidence", "probability_margin", "normalized_entropy",
            "forced_hold", "reason_codes", "model_hash", "prediction_hash",
        ])
        writer.writeheader()
        for record in history.records:
            writer.writerow({
                "prediction_id": record.prediction_id,
                "timestamp": record.timestamp,
                "raw_label": record.raw_label,
                "final_label": record.final_label,
                "confidence": record.confidence,
                "probability_margin": record.probability_margin,
                "normalized_entropy": record.normalized_entropy,
                "forced_hold": record.forced_hold,
                "reason_codes": "|".join(record.reason_codes),
                "model_hash": record.model_hash,
                "prediction_hash": record.prediction_hash,
            })
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
