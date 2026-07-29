from __future__ import annotations

"""
V28.3 Offline Ensemble Engine

Features:
- hard voting
- soft voting
- weighted soft voting
- confidence-weighted voting
- agreement score
- consensus confidence
- disagreement HOLD override
- model contribution tracking
- deterministic output
- SHA-256 integrity verification
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
from math import log
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "28.3"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class EnsembleError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise EnsembleError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise EnsembleError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ModelVote:
    model_id: str
    model_hash: str
    classes: tuple[int, ...]
    probabilities: tuple[Decimal, ...]
    weight: Decimal
    confidence: Decimal
    vote_hash: str


@dataclass(frozen=True)
class EnsemblePolicy:
    method: str = "CONFIDENCE_WEIGHTED"
    hold_label: int = 0
    min_agreement: Decimal = Decimal("0.60")
    min_consensus_confidence: Decimal = Decimal("0.55")
    max_entropy: Decimal = Decimal("0.85")
    force_hold_on_disagreement: bool = True

    def __post_init__(self) -> None:
        if self.method.upper() not in {
            "HARD",
            "SOFT",
            "WEIGHTED",
            "CONFIDENCE_WEIGHTED",
        }:
            raise EnsembleError("unsupported ensemble method")
        for name in ("min_agreement", "min_consensus_confidence", "max_entropy"):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise EnsembleError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class ModelContribution:
    model_id: str
    normalized_weight: Decimal
    predicted_label: int
    predicted_probability: Decimal
    contribution_to_final_label: Decimal


@dataclass(frozen=True)
class EnsembleResult:
    version: str
    ensemble_id: str
    method: str
    classes: tuple[int, ...]
    raw_label: int
    final_label: int
    class_probabilities: tuple[Decimal, ...]
    agreement_score: Decimal
    consensus_confidence: Decimal
    normalized_entropy: Decimal
    forced_hold: bool
    reason_codes: tuple[str, ...]
    contributions: tuple[ModelContribution, ...]
    input_hash: str
    result_hash: str


def _vote_payload(vote: ModelVote, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "model_id": vote.model_id,
        "model_hash": vote.model_hash,
        "classes": list(vote.classes),
        "probabilities": [str(value) for value in vote.probabilities],
        "weight": str(vote.weight),
        "confidence": str(vote.confidence),
    }
    if include_hash:
        payload["vote_hash"] = vote.vote_hash
    return payload


def _contribution_payload(item: ModelContribution) -> dict[str, Any]:
    return {
        "model_id": item.model_id,
        "normalized_weight": str(item.normalized_weight),
        "predicted_label": item.predicted_label,
        "predicted_probability": str(item.predicted_probability),
        "contribution_to_final_label": str(item.contribution_to_final_label),
    }


def _result_payload(result: EnsembleResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "ensemble_id": result.ensemble_id,
        "method": result.method,
        "classes": list(result.classes),
        "raw_label": result.raw_label,
        "final_label": result.final_label,
        "class_probabilities": [str(value) for value in result.class_probabilities],
        "agreement_score": str(result.agreement_score),
        "consensus_confidence": str(result.consensus_confidence),
        "normalized_entropy": str(result.normalized_entropy),
        "forced_hold": result.forced_hold,
        "reason_codes": list(result.reason_codes),
        "contributions": [_contribution_payload(item) for item in result.contributions],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise EnsembleError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def create_model_vote(
    *,
    model_id: str,
    model_hash: str,
    classes: Iterable[int],
    probabilities: Iterable[Any],
    weight: Any = 1,
) -> ModelVote:
    mid = model_id.strip()
    if not mid:
        raise EnsembleError("model_id is required")

    digest = _validate_sha256(model_hash, "model_hash")
    class_values = tuple(int(value) for value in classes)
    probability_values = tuple(_q(value) for value in probabilities)
    model_weight = _q(weight)

    if len(class_values) < 2 or len(class_values) != len(set(class_values)):
        raise EnsembleError("invalid class list")
    if len(class_values) != len(probability_values):
        raise EnsembleError("probability count does not match classes")
    if any(value < ZERO or value > ONE for value in probability_values):
        raise EnsembleError("probabilities must be between 0 and 1")
    if abs(sum(probability_values, ZERO) - ONE) > Decimal("0.000010"):
        raise EnsembleError("probabilities must sum to one")
    if model_weight <= ZERO:
        raise EnsembleError("model weight must be positive")

    difference = Decimal("1.000000") - sum(probability_values, ZERO)
    probability_values = probability_values[:-1] + (
        probability_values[-1] + difference,
    )
    confidence = max(probability_values)

    vote = ModelVote(
        model_id=mid,
        model_hash=digest,
        classes=class_values,
        probabilities=probability_values,
        weight=model_weight,
        confidence=confidence,
        vote_hash="",
    )
    return replace(vote, vote_hash=_hash(_vote_payload(vote)))


def verify_vote(vote: ModelVote) -> bool:
    _validate_sha256(vote.model_hash, "model_hash")
    if not vote.model_id:
        raise EnsembleError("model_id is required")
    if len(vote.classes) < 2 or len(vote.classes) != len(set(vote.classes)):
        raise EnsembleError("invalid vote classes")
    if len(vote.classes) != len(vote.probabilities):
        raise EnsembleError("vote probability count mismatch")
    if any(value < ZERO or value > ONE for value in vote.probabilities):
        raise EnsembleError("invalid probability")
    if sum(vote.probabilities, ZERO) != Decimal("1.000000"):
        raise EnsembleError("vote probabilities must sum to one")
    if vote.weight <= ZERO:
        raise EnsembleError("vote weight must be positive")
    if vote.confidence != max(vote.probabilities):
        raise EnsembleError("vote confidence mismatch")

    clean = replace(vote, vote_hash="")
    if vote.vote_hash != _hash(_vote_payload(clean)):
        raise EnsembleError("vote hash mismatch")
    return True


def _predicted_index(vote: ModelVote) -> int:
    return max(
        range(len(vote.probabilities)),
        key=lambda index: (vote.probabilities[index], -index),
    )


def _normalized_entropy(probabilities: tuple[Decimal, ...]) -> Decimal:
    if len(probabilities) <= 1:
        return ZERO
    entropy = 0.0
    for probability in probabilities:
        value = float(probability)
        if value > 0:
            entropy -= value * log(value)
    return _q(entropy / log(len(probabilities)))


def combine_votes(
    votes: Iterable[ModelVote],
    policy: EnsemblePolicy | None = None,
) -> EnsembleResult:
    selected = policy or EnsemblePolicy()
    items = tuple(votes)

    if len(items) < 2:
        raise EnsembleError("at least two model votes are required")
    if len({item.model_id for item in items}) != len(items):
        raise EnsembleError("duplicate model IDs detected")
    if len({item.model_hash for item in items}) != len(items):
        raise EnsembleError("duplicate model hashes detected")

    for item in items:
        verify_vote(item)

    classes = items[0].classes
    if any(item.classes != classes for item in items[1:]):
        raise EnsembleError("all votes must use the same class order")
    if selected.hold_label not in classes:
        raise EnsembleError("HOLD label is absent from ensemble classes")

    method = selected.method.upper()
    predicted_indices = tuple(_predicted_index(item) for item in items)
    predicted_labels = tuple(classes[index] for index in predicted_indices)

    if method == "HARD":
        counts = {
            label: predicted_labels.count(label)
            for label in classes
        }
        top_count = max(counts.values())
        candidate_labels = [
            label for label in classes if counts[label] == top_count
        ]
        raw_label = min(
            candidate_labels,
            key=lambda label: classes.index(label),
        )
        class_probabilities = tuple(
            _q(Decimal(counts[label]) / Decimal(len(items)))
            for label in classes
        )
        effective_weights = tuple(ONE for _ in items)
    else:
        if method == "SOFT":
            effective_weights = tuple(ONE for _ in items)
        elif method == "WEIGHTED":
            effective_weights = tuple(item.weight for item in items)
        else:
            effective_weights = tuple(
                _q(item.weight * item.confidence)
                for item in items
            )

        total_weight = sum(effective_weights, ZERO)
        if total_weight <= ZERO:
            raise EnsembleError("ensemble effective weight must be positive")

        raw_values = []
        for class_index in range(len(classes)):
            weighted_sum = sum(
                item.probabilities[class_index] * effective_weight
                for item, effective_weight in zip(items, effective_weights)
            )
            raw_values.append(_q(weighted_sum / total_weight))

        difference = Decimal("1.000000") - sum(raw_values, ZERO)
        raw_values[-1] += difference
        class_probabilities = tuple(raw_values)
        raw_index = max(
            range(len(class_probabilities)),
            key=lambda index: (class_probabilities[index], -index),
        )
        raw_label = classes[raw_index]

    agreement_count = predicted_labels.count(raw_label)
    agreement_score = _q(
        Decimal(agreement_count) / Decimal(len(items))
    )
    consensus_confidence = max(class_probabilities)
    entropy = _normalized_entropy(class_probabilities)

    reasons = []
    if agreement_score < _d(selected.min_agreement):
        reasons.append("LOW_AGREEMENT")
    if consensus_confidence < _d(selected.min_consensus_confidence):
        reasons.append("LOW_CONSENSUS_CONFIDENCE")
    if entropy > _d(selected.max_entropy):
        reasons.append("HIGH_ENTROPY")

    forced_hold = bool(reasons) and selected.force_hold_on_disagreement
    final_label = selected.hold_label if forced_hold else raw_label

    total_effective_weight = sum(effective_weights, ZERO)
    final_index = classes.index(raw_label)
    contributions = tuple(
        ModelContribution(
            model_id=item.model_id,
            normalized_weight=_q(weight / total_effective_weight),
            predicted_label=classes[predicted_index],
            predicted_probability=item.probabilities[predicted_index],
            contribution_to_final_label=_q(
                weight
                / total_effective_weight
                * item.probabilities[final_index]
            ),
        )
        for item, weight, predicted_index in zip(
            items,
            effective_weights,
            predicted_indices,
        )
    )

    input_hash = _hash({
        "votes": [_vote_payload(item, include_hash=True) for item in items],
        "policy": {
            key: str(value)
            for key, value in selected.__dict__.items()
        },
    })
    ensemble_id = f"ENS-{input_hash[:16].upper()}"

    result = EnsembleResult(
        version=VERSION,
        ensemble_id=ensemble_id,
        method=method,
        classes=classes,
        raw_label=raw_label,
        final_label=final_label,
        class_probabilities=class_probabilities,
        agreement_score=agreement_score,
        consensus_confidence=consensus_confidence,
        normalized_entropy=entropy,
        forced_hold=forced_hold,
        reason_codes=tuple(sorted(reasons)),
        contributions=contributions,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: EnsembleResult) -> bool:
    if result.version != VERSION:
        raise EnsembleError("unsupported ensemble version")
    if not result.ensemble_id.startswith("ENS-"):
        raise EnsembleError("invalid ensemble ID")
    if result.method not in {
        "HARD",
        "SOFT",
        "WEIGHTED",
        "CONFIDENCE_WEIGHTED",
    }:
        raise EnsembleError("invalid ensemble method")
    if len(result.classes) < 2:
        raise EnsembleError("invalid ensemble classes")
    if len(result.class_probabilities) != len(result.classes):
        raise EnsembleError("class probability count mismatch")
    if sum(result.class_probabilities, ZERO) != Decimal("1.000000"):
        raise EnsembleError("ensemble probabilities must sum to one")
    if result.raw_label not in result.classes:
        raise EnsembleError("raw label is absent from classes")
    if result.consensus_confidence != max(result.class_probabilities):
        raise EnsembleError("consensus confidence mismatch")
    if result.forced_hold and not result.reason_codes:
        raise EnsembleError("forced HOLD requires reason codes")
    if not result.contributions:
        raise EnsembleError("contributions cannot be empty")
    if sum(
        (item.normalized_weight for item in result.contributions),
        ZERO,
    ) != Decimal("1.000000"):
        raise EnsembleError("contribution weights must sum to one")

    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise EnsembleError("ensemble result hash mismatch")
    return True


def save_result(result: EnsembleResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            _result_payload(result, include_hash=True),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> EnsembleResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = EnsembleResult(
        version=payload["version"],
        ensemble_id=payload["ensemble_id"],
        method=payload["method"],
        classes=tuple(int(value) for value in payload["classes"]),
        raw_label=int(payload["raw_label"]),
        final_label=int(payload["final_label"]),
        class_probabilities=tuple(
            _d(value) for value in payload["class_probabilities"]
        ),
        agreement_score=_d(payload["agreement_score"]),
        consensus_confidence=_d(payload["consensus_confidence"]),
        normalized_entropy=_d(payload["normalized_entropy"]),
        forced_hold=bool(payload["forced_hold"]),
        reason_codes=tuple(payload["reason_codes"]),
        contributions=tuple(
            ModelContribution(
                model_id=item["model_id"],
                normalized_weight=_d(item["normalized_weight"]),
                predicted_label=int(item["predicted_label"]),
                predicted_probability=_d(item["predicted_probability"]),
                contribution_to_final_label=_d(
                    item["contribution_to_final_label"]
                ),
            )
            for item in payload["contributions"]
        ),
        input_hash=payload["input_hash"],
        result_hash=payload["result_hash"],
    )
    verify_result(result)
    return result


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
