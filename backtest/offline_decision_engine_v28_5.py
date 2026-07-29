from __future__ import annotations

"""
V28.5 Offline Decision Engine

Features:
- BUY / HOLD / SELL final decision
- confidence threshold
- agreement threshold
- entropy threshold
- risk threshold
- ensemble signal integration
- HOLD overrides
- position-size recommendation
- reason-code generation
- deterministic output
- SHA-256 integrity verification
- decision history
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
from typing import Any, Iterable
import json

VERSION = "28.5"
ZERO = Decimal("0")
ONE = Decimal("1")
SIX = Decimal("0.000001")


class DecisionError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise DecisionError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise DecisionError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(SIX, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DecisionPolicy:
    hold_label: int = 0
    min_confidence: Decimal = Decimal("0.55")
    min_agreement: Decimal = Decimal("0.60")
    max_entropy: Decimal = Decimal("0.85")
    max_risk_score: Decimal = Decimal("0.65")
    max_position_fraction: Decimal = Decimal("0.10")
    min_position_fraction: Decimal = Decimal("0.01")
    force_hold_on_rule_failure: bool = True

    def __post_init__(self) -> None:
        for name in (
            "min_confidence",
            "min_agreement",
            "max_entropy",
            "max_risk_score",
            "max_position_fraction",
            "min_position_fraction",
        ):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise DecisionError(f"{name} must be between 0 and 1")
        if _d(self.min_position_fraction) > _d(self.max_position_fraction):
            raise DecisionError("min_position_fraction cannot exceed max_position_fraction")


@dataclass(frozen=True)
class DecisionInput:
    decision_id: str
    timestamp: str
    symbol: str
    ensemble_label: int
    confidence: Decimal
    agreement: Decimal
    entropy: Decimal
    risk_score: Decimal
    expected_return_pct: Decimal
    model_hash: str
    ensemble_hash: str


@dataclass(frozen=True)
class DecisionRecord:
    version: str
    decision_id: str
    timestamp: str
    symbol: str
    raw_label: int
    final_label: int
    confidence: Decimal
    agreement: Decimal
    entropy: Decimal
    risk_score: Decimal
    expected_return_pct: Decimal
    recommended_position_fraction: Decimal
    forced_hold: bool
    reason_codes: tuple[str, ...]
    model_hash: str
    ensemble_hash: str
    input_hash: str
    decision_hash: str


@dataclass(frozen=True)
class DecisionHistory:
    version: str
    decisions: tuple[DecisionRecord, ...]
    history_hash: str


def _validate_sha256(value: str, field_name: str) -> str:
    digest = value.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise DecisionError(f"{field_name} must be a SHA-256 hex digest")
    return digest


def _record_payload(record: DecisionRecord, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": record.version,
        "decision_id": record.decision_id,
        "timestamp": record.timestamp,
        "symbol": record.symbol,
        "raw_label": record.raw_label,
        "final_label": record.final_label,
        "confidence": str(record.confidence),
        "agreement": str(record.agreement),
        "entropy": str(record.entropy),
        "risk_score": str(record.risk_score),
        "expected_return_pct": str(record.expected_return_pct),
        "recommended_position_fraction": str(record.recommended_position_fraction),
        "forced_hold": record.forced_hold,
        "reason_codes": list(record.reason_codes),
        "model_hash": record.model_hash,
        "ensemble_hash": record.ensemble_hash,
        "input_hash": record.input_hash,
    }
    if include_hash:
        payload["decision_hash"] = record.decision_hash
    return payload


def _history_payload(history: DecisionHistory, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": history.version,
        "decisions": [
            _record_payload(record, include_hash=True)
            for record in history.decisions
        ],
    }
    if include_hash:
        payload["history_hash"] = history.history_hash
    return payload


def _position_fraction(
    *,
    confidence: Decimal,
    agreement: Decimal,
    risk_score: Decimal,
    expected_return_pct: Decimal,
    policy: DecisionPolicy,
) -> Decimal:
    if expected_return_pct <= ZERO:
        return ZERO

    quality = (
        confidence * Decimal("0.45")
        + agreement * Decimal("0.35")
        + (ONE - risk_score) * Decimal("0.20")
    )
    return_component = min(
        ONE,
        max(ZERO, expected_return_pct / Decimal("10")),
    )
    raw = _d(policy.max_position_fraction) * quality * (
        Decimal("0.70") + return_component * Decimal("0.30")
    )
    bounded = min(_d(policy.max_position_fraction), raw)
    if bounded < _d(policy.min_position_fraction):
        return _d(policy.min_position_fraction)
    return _q(bounded)


def make_decision(
    item: DecisionInput,
    policy: DecisionPolicy | None = None,
) -> DecisionRecord:
    selected = policy or DecisionPolicy()

    decision_id = item.decision_id.strip()
    timestamp = item.timestamp.strip()
    symbol = item.symbol.strip().upper()

    if not decision_id or not timestamp or not symbol:
        raise DecisionError("decision_id, timestamp, and symbol are required")

    confidence = _q(item.confidence)
    agreement = _q(item.agreement)
    entropy = _q(item.entropy)
    risk_score = _q(item.risk_score)
    expected_return_pct = _q(item.expected_return_pct)

    for name, value in (
        ("confidence", confidence),
        ("agreement", agreement),
        ("entropy", entropy),
        ("risk_score", risk_score),
    ):
        if value < ZERO or value > ONE:
            raise DecisionError(f"{name} must be between 0 and 1")

    model_hash = _validate_sha256(item.model_hash, "model_hash")
    ensemble_hash = _validate_sha256(item.ensemble_hash, "ensemble_hash")

    reasons = []
    if confidence < _d(selected.min_confidence):
        reasons.append("LOW_CONFIDENCE")
    if agreement < _d(selected.min_agreement):
        reasons.append("LOW_AGREEMENT")
    if entropy > _d(selected.max_entropy):
        reasons.append("HIGH_ENTROPY")
    if risk_score > _d(selected.max_risk_score):
        reasons.append("RISK_LIMIT_EXCEEDED")
    if item.ensemble_label != selected.hold_label and expected_return_pct <= ZERO:
        reasons.append("NON_POSITIVE_EXPECTED_RETURN")

    forced_hold = bool(reasons) and selected.force_hold_on_rule_failure
    final_label = selected.hold_label if forced_hold else int(item.ensemble_label)

    if final_label == selected.hold_label:
        position_fraction = ZERO
    else:
        position_fraction = _position_fraction(
            confidence=confidence,
            agreement=agreement,
            risk_score=risk_score,
            expected_return_pct=expected_return_pct,
            policy=selected,
        )

    input_hash = _hash({
        "decision_id": decision_id,
        "timestamp": timestamp,
        "symbol": symbol,
        "ensemble_label": int(item.ensemble_label),
        "confidence": str(confidence),
        "agreement": str(agreement),
        "entropy": str(entropy),
        "risk_score": str(risk_score),
        "expected_return_pct": str(expected_return_pct),
        "model_hash": model_hash,
        "ensemble_hash": ensemble_hash,
        "policy": {key: str(value) for key, value in selected.__dict__.items()},
    })

    record = DecisionRecord(
        version=VERSION,
        decision_id=decision_id,
        timestamp=timestamp,
        symbol=symbol,
        raw_label=int(item.ensemble_label),
        final_label=final_label,
        confidence=confidence,
        agreement=agreement,
        entropy=entropy,
        risk_score=risk_score,
        expected_return_pct=expected_return_pct,
        recommended_position_fraction=position_fraction,
        forced_hold=forced_hold,
        reason_codes=tuple(sorted(reasons)),
        model_hash=model_hash,
        ensemble_hash=ensemble_hash,
        input_hash=input_hash,
        decision_hash="",
    )
    return replace(record, decision_hash=_hash(_record_payload(record)))


def verify_record(record: DecisionRecord) -> bool:
    if record.version != VERSION:
        raise DecisionError("unsupported decision version")
    if not record.decision_id or not record.timestamp or not record.symbol:
        raise DecisionError("invalid decision identity")
    _validate_sha256(record.model_hash, "model_hash")
    _validate_sha256(record.ensemble_hash, "ensemble_hash")

    for name, value in (
        ("confidence", record.confidence),
        ("agreement", record.agreement),
        ("entropy", record.entropy),
        ("risk_score", record.risk_score),
        ("recommended_position_fraction", record.recommended_position_fraction),
    ):
        if value < ZERO or value > ONE:
            raise DecisionError(f"{name} out of range")

    if record.forced_hold and not record.reason_codes:
        raise DecisionError("forced HOLD requires reason codes")
    if record.final_label == 0 and record.recommended_position_fraction != ZERO:
        raise DecisionError("HOLD decision must have zero position size")
    if record.final_label != 0 and record.recommended_position_fraction <= ZERO:
        raise DecisionError("active decision requires positive position size")

    clean = replace(record, decision_hash="")
    if record.decision_hash != _hash(_record_payload(clean)):
        raise DecisionError("decision hash mismatch")
    return True


def create_history(records: Iterable[DecisionRecord]) -> DecisionHistory:
    decisions = tuple(records)
    if not decisions:
        raise DecisionError("decision history cannot be empty")
    if len({record.decision_id for record in decisions}) != len(decisions):
        raise DecisionError("duplicate decision IDs detected")
    for record in decisions:
        verify_record(record)

    history = DecisionHistory(
        version=VERSION,
        decisions=decisions,
        history_hash="",
    )
    return replace(history, history_hash=_hash(_history_payload(history)))


def verify_history(history: DecisionHistory) -> bool:
    if history.version != VERSION:
        raise DecisionError("unsupported history version")
    if not history.decisions:
        raise DecisionError("history cannot be empty")
    if len({record.decision_id for record in history.decisions}) != len(history.decisions):
        raise DecisionError("duplicate decision IDs detected")
    for record in history.decisions:
        verify_record(record)

    clean = replace(history, history_hash="")
    if history.history_hash != _hash(_history_payload(clean)):
        raise DecisionError("history hash mismatch")
    return True


def save_history(history: DecisionHistory, path: str | Path) -> Path:
    verify_history(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_history_payload(history, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_history(path: str | Path) -> DecisionHistory:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    decisions = tuple(
        DecisionRecord(
            version=item["version"],
            decision_id=item["decision_id"],
            timestamp=item["timestamp"],
            symbol=item["symbol"],
            raw_label=int(item["raw_label"]),
            final_label=int(item["final_label"]),
            confidence=_d(item["confidence"]),
            agreement=_d(item["agreement"]),
            entropy=_d(item["entropy"]),
            risk_score=_d(item["risk_score"]),
            expected_return_pct=_d(item["expected_return_pct"]),
            recommended_position_fraction=_d(item["recommended_position_fraction"]),
            forced_hold=bool(item["forced_hold"]),
            reason_codes=tuple(item["reason_codes"]),
            model_hash=item["model_hash"],
            ensemble_hash=item["ensemble_hash"],
            input_hash=item["input_hash"],
            decision_hash=item["decision_hash"],
        )
        for item in payload["decisions"]
    )
    history = DecisionHistory(
        version=payload["version"],
        decisions=decisions,
        history_hash=payload["history_hash"],
    )
    verify_history(history)
    return history


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
