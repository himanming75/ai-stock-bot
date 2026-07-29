from __future__ import annotations

"""
V25.4 Offline Strategy Engine

Combines multiple deterministic strategy models:
- trend following
- momentum
- mean reversion
- breakout

The engine resolves conflicting strategy votes, applies configurable weights,
produces BUY/HOLD/SELL decisions, calculates confidence, and protects results
with canonical hashes.

Safety boundary:
- no network access
- no broker/account APIs
- no order creation/submission
- no live execution
"""

from dataclasses import asdict, dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

VERSION = "25.4"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class StrategyError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise StrategyError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise StrategyError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise StrategyError("invalid symbol")
    return result


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StrategyPolicy:
    trend_weight: Decimal = Decimal("0.30")
    momentum_weight: Decimal = Decimal("0.25")
    mean_reversion_weight: Decimal = Decimal("0.20")
    breakout_weight: Decimal = Decimal("0.25")
    buy_threshold: Decimal = Decimal("0.25")
    sell_threshold: Decimal = Decimal("-0.25")
    min_confidence: Decimal = Decimal("0.55")
    max_abs_score: Decimal = Decimal("1.00")

    def __post_init__(self) -> None:
        weights = (
            _d(self.trend_weight),
            _d(self.momentum_weight),
            _d(self.mean_reversion_weight),
            _d(self.breakout_weight),
        )
        if any(w < ZERO for w in weights):
            raise StrategyError("strategy weights cannot be negative")
        if sum(weights) <= ZERO:
            raise StrategyError("at least one strategy weight must be positive")
        if _d(self.sell_threshold) >= _d(self.buy_threshold):
            raise StrategyError("sell threshold must be below buy threshold")
        if _d(self.min_confidence) < ZERO or _d(self.min_confidence) > Decimal("1"):
            raise StrategyError("min_confidence must be between 0 and 1")
        if _d(self.max_abs_score) <= ZERO:
            raise StrategyError("max_abs_score must be positive")


@dataclass(frozen=True)
class StrategyInput:
    symbol: str
    close: Decimal
    ema_fast: Decimal
    ema_slow: Decimal
    rsi: Decimal
    macd: Decimal
    macd_signal: Decimal
    atr: Decimal
    highest_high: Decimal
    lowest_low: Decimal
    volume_ratio: Decimal
    return_5: Decimal
    return_20: Decimal
    signal_bias: Decimal = ZERO


@dataclass(frozen=True)
class StrategyVote:
    name: str
    score: Decimal
    weight: Decimal
    weighted_score: Decimal
    reason: str


@dataclass(frozen=True)
class StrategyDecision:
    version: str
    symbol: str
    action: str
    composite_score: Decimal
    confidence: Decimal
    bullish_weight: Decimal
    bearish_weight: Decimal
    neutral_weight: Decimal
    conflict_detected: bool
    votes: tuple[StrategyVote, ...]
    reason_codes: tuple[str, ...]
    input_hash: str
    decision_hash: str


def _input_payload(data: StrategyInput) -> dict[str, str]:
    return {
        "symbol": data.symbol,
        "close": str(data.close),
        "ema_fast": str(data.ema_fast),
        "ema_slow": str(data.ema_slow),
        "rsi": str(data.rsi),
        "macd": str(data.macd),
        "macd_signal": str(data.macd_signal),
        "atr": str(data.atr),
        "highest_high": str(data.highest_high),
        "lowest_low": str(data.lowest_low),
        "volume_ratio": str(data.volume_ratio),
        "return_5": str(data.return_5),
        "return_20": str(data.return_20),
        "signal_bias": str(data.signal_bias),
    }


def _policy_payload(policy: StrategyPolicy) -> dict[str, str]:
    raw = asdict(policy)
    return {k: str(v) for k, v in raw.items()}


def _vote_payload(vote: StrategyVote) -> dict[str, str]:
    return {
        "name": vote.name,
        "score": str(vote.score),
        "weight": str(vote.weight),
        "weighted_score": str(vote.weighted_score),
        "reason": vote.reason,
    }


def _decision_payload(decision: StrategyDecision, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": decision.version,
        "symbol": decision.symbol,
        "action": decision.action,
        "composite_score": str(decision.composite_score),
        "confidence": str(decision.confidence),
        "bullish_weight": str(decision.bullish_weight),
        "bearish_weight": str(decision.bearish_weight),
        "neutral_weight": str(decision.neutral_weight),
        "conflict_detected": decision.conflict_detected,
        "votes": [_vote_payload(v) for v in decision.votes],
        "reason_codes": list(decision.reason_codes),
        "input_hash": decision.input_hash,
    }
    if include_hash:
        payload["decision_hash"] = decision.decision_hash
    return payload


def _normalize_input(data: StrategyInput) -> StrategyInput:
    normalized = StrategyInput(
        symbol=_symbol(data.symbol),
        close=_q(data.close),
        ema_fast=_q(data.ema_fast),
        ema_slow=_q(data.ema_slow),
        rsi=_q(data.rsi),
        macd=_q(data.macd),
        macd_signal=_q(data.macd_signal),
        atr=_q(data.atr),
        highest_high=_q(data.highest_high),
        lowest_low=_q(data.lowest_low),
        volume_ratio=_q(data.volume_ratio),
        return_5=_q(data.return_5),
        return_20=_q(data.return_20),
        signal_bias=_q(data.signal_bias),
    )
    if normalized.close <= ZERO:
        raise StrategyError("close must be positive")
    if normalized.ema_fast <= ZERO or normalized.ema_slow <= ZERO:
        raise StrategyError("EMA values must be positive")
    if normalized.atr <= ZERO:
        raise StrategyError("ATR must be positive")
    if normalized.highest_high < normalized.lowest_low:
        raise StrategyError("highest_high cannot be below lowest_low")
    if normalized.rsi < ZERO or normalized.rsi > Decimal("100"):
        raise StrategyError("RSI must be between 0 and 100")
    if normalized.volume_ratio < ZERO:
        raise StrategyError("volume_ratio cannot be negative")
    if abs(normalized.signal_bias) > Decimal("1"):
        raise StrategyError("signal_bias must be between -1 and 1")
    return normalized


def _bounded(value: Decimal) -> Decimal:
    return max(Decimal("-1"), min(Decimal("1"), value))


def _trend_vote(data: StrategyInput, weight: Decimal) -> StrategyVote:
    spread = (data.ema_fast - data.ema_slow) / data.close
    score = _bounded(spread * Decimal("20"))
    reason = "FAST_EMA_ABOVE_SLOW" if score > ZERO else (
        "FAST_EMA_BELOW_SLOW" if score < ZERO else "EMA_NEUTRAL"
    )
    return StrategyVote("TREND", _q(score), _q(weight), _q(score * weight), reason)


def _momentum_vote(data: StrategyInput, weight: Decimal) -> StrategyVote:
    macd_component = (data.macd - data.macd_signal) / max(data.atr, Decimal("0.0001"))
    return_component = data.return_5 * Decimal("5") + data.return_20 * Decimal("2")
    score = _bounded(macd_component * Decimal("0.35") + return_component)
    reason = "POSITIVE_MOMENTUM" if score > ZERO else (
        "NEGATIVE_MOMENTUM" if score < ZERO else "MOMENTUM_NEUTRAL"
    )
    return StrategyVote("MOMENTUM", _q(score), _q(weight), _q(score * weight), reason)


def _mean_reversion_vote(data: StrategyInput, weight: Decimal) -> StrategyVote:
    if data.rsi <= Decimal("30"):
        score = (Decimal("50") - data.rsi) / Decimal("20")
        reason = "OVERSOLD"
    elif data.rsi >= Decimal("70"):
        score = -(data.rsi - Decimal("50")) / Decimal("20")
        reason = "OVERBOUGHT"
    else:
        score = ZERO
        reason = "RSI_NEUTRAL"
    score = _bounded(score)
    return StrategyVote("MEAN_REVERSION", _q(score), _q(weight), _q(score * weight), reason)


def _breakout_vote(data: StrategyInput, weight: Decimal) -> StrategyVote:
    tolerance = max(data.atr * Decimal("0.10"), Decimal("0.0001"))
    if data.close >= data.highest_high - tolerance and data.volume_ratio >= Decimal("1.20"):
        score = min(Decimal("1"), Decimal("0.65") + (data.volume_ratio - Decimal("1.20")) * Decimal("0.25"))
        reason = "UPSIDE_BREAKOUT"
    elif data.close <= data.lowest_low + tolerance and data.volume_ratio >= Decimal("1.20"):
        score = -min(Decimal("1"), Decimal("0.65") + (data.volume_ratio - Decimal("1.20")) * Decimal("0.25"))
        reason = "DOWNSIDE_BREAKOUT"
    else:
        score = ZERO
        reason = "NO_BREAKOUT"
    return StrategyVote("BREAKOUT", _q(score), _q(weight), _q(score * weight), reason)


def evaluate_strategies(
    data: StrategyInput,
    policy: StrategyPolicy | None = None,
) -> StrategyDecision:
    selected = policy or StrategyPolicy()
    item = _normalize_input(data)

    raw_weights = {
        "TREND": _d(selected.trend_weight),
        "MOMENTUM": _d(selected.momentum_weight),
        "MEAN_REVERSION": _d(selected.mean_reversion_weight),
        "BREAKOUT": _d(selected.breakout_weight),
    }
    total_weight = sum(raw_weights.values())
    weights = {k: v / total_weight for k, v in raw_weights.items()}

    votes = (
        _trend_vote(item, weights["TREND"]),
        _momentum_vote(item, weights["MOMENTUM"]),
        _mean_reversion_vote(item, weights["MEAN_REVERSION"]),
        _breakout_vote(item, weights["BREAKOUT"]),
    )

    composite = sum((v.weighted_score for v in votes), ZERO)
    composite += item.signal_bias * Decimal("0.10")
    max_abs = _d(selected.max_abs_score)
    composite = max(-max_abs, min(max_abs, composite))
    composite = _q(composite)

    bullish = _q(sum((v.weight for v in votes if v.score > ZERO), ZERO))
    bearish = _q(sum((v.weight for v in votes if v.score < ZERO), ZERO))
    neutral = _q(sum((v.weight for v in votes if v.score == ZERO), ZERO))
    conflict = bullish > ZERO and bearish > ZERO

    directional_weight = max(bullish, bearish)
    agreement = abs(bullish - bearish)
    score_strength = min(Decimal("1"), abs(composite) / max_abs)
    confidence = _q(min(Decimal("1"), score_strength * Decimal("0.65") + agreement * Decimal("0.35")))

    reasons: list[str] = []
    if conflict:
        reasons.append("STRATEGY_CONFLICT")
    if confidence < _d(selected.min_confidence):
        reasons.append("LOW_CONFIDENCE")

    if composite >= _d(selected.buy_threshold) and confidence >= _d(selected.min_confidence):
        action = "BUY"
    elif composite <= _d(selected.sell_threshold) and confidence >= _d(selected.min_confidence):
        action = "SELL"
    else:
        action = "HOLD"

    if action == "HOLD":
        reasons.append("HOLD_POLICY")
    if directional_weight == ZERO:
        reasons.append("NO_DIRECTIONAL_CONSENSUS")

    input_hash = _hash({
        "input": _input_payload(item),
        "policy": _policy_payload(selected),
    })

    decision = StrategyDecision(
        version=VERSION,
        symbol=item.symbol,
        action=action,
        composite_score=composite,
        confidence=confidence,
        bullish_weight=bullish,
        bearish_weight=bearish,
        neutral_weight=neutral,
        conflict_detected=conflict,
        votes=votes,
        reason_codes=tuple(sorted(set(reasons))),
        input_hash=input_hash,
        decision_hash="",
    )
    return replace(decision, decision_hash=_hash(_decision_payload(decision)))


def verify_decision(decision: StrategyDecision) -> bool:
    if decision.version != VERSION:
        raise StrategyError("unsupported strategy decision version")
    if decision.action not in {"BUY", "HOLD", "SELL"}:
        raise StrategyError("invalid action")
    if decision.confidence < ZERO or decision.confidence > Decimal("1"):
        raise StrategyError("confidence out of range")
    if abs(decision.composite_score) > Decimal("1"):
        raise StrategyError("composite score out of range")
    if len({vote.name for vote in decision.votes}) != len(decision.votes):
        raise StrategyError("duplicate strategy votes")
    if _q(decision.bullish_weight + decision.bearish_weight + decision.neutral_weight) != Decimal("1.0000"):
        raise StrategyError("strategy weights do not sum to 1")
    clean = replace(decision, decision_hash="")
    if decision.decision_hash != _hash(_decision_payload(clean)):
        raise StrategyError("decision hash mismatch")
    return True


def save_decision(decision: StrategyDecision, path: str | Path) -> Path:
    verify_decision(decision)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_decision_payload(decision, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_decision(path: str | Path) -> StrategyDecision:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    votes = tuple(
        StrategyVote(
            name=v["name"],
            score=_d(v["score"]),
            weight=_d(v["weight"]),
            weighted_score=_d(v["weighted_score"]),
            reason=v["reason"],
        )
        for v in payload["votes"]
    )
    decision = StrategyDecision(
        version=payload["version"],
        symbol=payload["symbol"],
        action=payload["action"],
        composite_score=_d(payload["composite_score"]),
        confidence=_d(payload["confidence"]),
        bullish_weight=_d(payload["bullish_weight"]),
        bearish_weight=_d(payload["bearish_weight"]),
        neutral_weight=_d(payload["neutral_weight"]),
        conflict_detected=bool(payload["conflict_detected"]),
        votes=votes,
        reason_codes=tuple(payload["reason_codes"]),
        input_hash=payload["input_hash"],
        decision_hash=payload["decision_hash"],
    )
    verify_decision(decision)
    return decision


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
