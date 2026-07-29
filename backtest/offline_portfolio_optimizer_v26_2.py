from __future__ import annotations

"""
V26.2 Offline Portfolio Optimizer

Deterministic allocation models:
- Equal Weight
- Inverse Volatility
- Risk Parity approximation
- Capped Kelly
- Dynamic Blend

The module enforces symbol caps, cash reserve, minimum/maximum asset counts,
canonical hashing, JSON persistence, and tamper detection.

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
from typing import Any, Iterable, Mapping
import json

VERSION = "26.2"
ZERO = Decimal("0")
ONE = Decimal("1")
FOUR = Decimal("0.0001")


class OptimizerError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise OptimizerError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise OptimizerError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(c.isalnum() or c in ".-" for c in result):
        raise OptimizerError("invalid symbol")
    return result


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AssetStats:
    symbol: str
    expected_return: Decimal
    volatility: Decimal
    win_rate: Decimal
    average_win: Decimal
    average_loss: Decimal
    confidence: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class OptimizerPolicy:
    method: str = "DYNAMIC"
    cash_reserve_pct: Decimal = Decimal("0.10")
    max_symbol_weight: Decimal = Decimal("0.35")
    min_symbol_weight: Decimal = Decimal("0.02")
    max_assets: int = 8
    kelly_cap: Decimal = Decimal("0.25")
    dynamic_equal_weight: Decimal = Decimal("0.20")
    dynamic_inverse_vol_weight: Decimal = Decimal("0.35")
    dynamic_risk_parity_weight: Decimal = Decimal("0.25")
    dynamic_kelly_weight: Decimal = Decimal("0.20")

    def __post_init__(self) -> None:
        method = self.method.upper()
        if method not in {"EQUAL", "INVERSE_VOL", "RISK_PARITY", "KELLY", "DYNAMIC"}:
            raise OptimizerError("unsupported optimization method")
        for name in ("cash_reserve_pct", "max_symbol_weight", "min_symbol_weight", "kelly_cap"):
            value = _d(getattr(self, name))
            if value < ZERO or value > ONE:
                raise OptimizerError(f"{name} must be between 0 and 1")
        if _d(self.min_symbol_weight) > _d(self.max_symbol_weight):
            raise OptimizerError("minimum symbol weight exceeds maximum symbol weight")
        if self.max_assets <= 0:
            raise OptimizerError("max_assets must be positive")
        blend = (
            _d(self.dynamic_equal_weight)
            + _d(self.dynamic_inverse_vol_weight)
            + _d(self.dynamic_risk_parity_weight)
            + _d(self.dynamic_kelly_weight)
        )
        if method == "DYNAMIC" and blend <= ZERO:
            raise OptimizerError("dynamic blend weights must sum to a positive value")
        for name in (
            "dynamic_equal_weight",
            "dynamic_inverse_vol_weight",
            "dynamic_risk_parity_weight",
            "dynamic_kelly_weight",
        ):
            if _d(getattr(self, name)) < ZERO:
                raise OptimizerError(f"{name} cannot be negative")


@dataclass(frozen=True)
class Allocation:
    symbol: str
    weight: Decimal
    method_score: Decimal
    risk_contribution: Decimal


@dataclass(frozen=True)
class OptimizationResult:
    version: str
    method: str
    invested_weight: Decimal
    cash_weight: Decimal
    allocations: tuple[Allocation, ...]
    input_hash: str
    result_hash: str


def _stats_payload(stats: AssetStats) -> dict[str, str]:
    return {
        "symbol": stats.symbol,
        "expected_return": str(stats.expected_return),
        "volatility": str(stats.volatility),
        "win_rate": str(stats.win_rate),
        "average_win": str(stats.average_win),
        "average_loss": str(stats.average_loss),
        "confidence": str(stats.confidence),
    }


def _policy_payload(policy: OptimizerPolicy) -> dict[str, Any]:
    raw = asdict(policy)
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in raw.items()
    }


def _allocation_payload(allocation: Allocation) -> dict[str, str]:
    return {
        "symbol": allocation.symbol,
        "weight": str(allocation.weight),
        "method_score": str(allocation.method_score),
        "risk_contribution": str(allocation.risk_contribution),
    }


def _result_payload(result: OptimizationResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "method": result.method,
        "invested_weight": str(result.invested_weight),
        "cash_weight": str(result.cash_weight),
        "allocations": [_allocation_payload(a) for a in result.allocations],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_stats(items: Iterable[AssetStats]) -> tuple[AssetStats, ...]:
    normalized = []
    for item in items:
        symbol = _symbol(item.symbol)
        expected_return = _d(item.expected_return)
        volatility = _d(item.volatility)
        win_rate = _d(item.win_rate)
        average_win = _d(item.average_win)
        average_loss = abs(_d(item.average_loss))
        confidence = _d(item.confidence)

        if volatility <= ZERO:
            raise OptimizerError("volatility must be positive")
        if win_rate < ZERO or win_rate > ONE:
            raise OptimizerError("win_rate must be between 0 and 1")
        if average_win < ZERO or average_loss < ZERO:
            raise OptimizerError("average win/loss must be non-negative")
        if confidence < ZERO or confidence > ONE:
            raise OptimizerError("confidence must be between 0 and 1")

        normalized.append(AssetStats(
            symbol=symbol,
            expected_return=_q(expected_return),
            volatility=_q(volatility),
            win_rate=_q(win_rate),
            average_win=_q(average_win),
            average_loss=_q(average_loss),
            confidence=_q(confidence),
        ))

    normalized.sort(key=lambda item: item.symbol)
    if not normalized:
        raise OptimizerError("asset statistics cannot be empty")
    if len({item.symbol for item in normalized}) != len(normalized):
        raise OptimizerError("duplicate symbols detected")
    return tuple(normalized)


def _normalize_scores(scores: Mapping[str, Decimal]) -> dict[str, Decimal]:
    positives = {symbol: max(score, ZERO) for symbol, score in scores.items()}
    total = sum(positives.values(), ZERO)
    if total <= ZERO:
        count = Decimal(len(positives))
        return {symbol: ONE / count for symbol in positives}
    return {symbol: value / total for symbol, value in positives.items()}


def _equal_scores(stats: tuple[AssetStats, ...]) -> dict[str, Decimal]:
    return {item.symbol: ONE for item in stats}


def _inverse_vol_scores(stats: tuple[AssetStats, ...]) -> dict[str, Decimal]:
    return {item.symbol: ONE / item.volatility for item in stats}


def _risk_parity_scores(stats: tuple[AssetStats, ...]) -> dict[str, Decimal]:
    return {
        item.symbol: item.confidence / (item.volatility * item.volatility)
        for item in stats
    }


def _kelly_score(item: AssetStats, cap: Decimal) -> Decimal:
    if item.average_win <= ZERO or item.average_loss <= ZERO:
        return ZERO
    b = item.average_win / item.average_loss
    q = ONE - item.win_rate
    raw = (b * item.win_rate - q) / b
    return max(ZERO, min(cap, raw * item.confidence))


def _kelly_scores(stats: tuple[AssetStats, ...], cap: Decimal) -> dict[str, Decimal]:
    return {item.symbol: _kelly_score(item, cap) for item in stats}


def _blend_scores(
    stats: tuple[AssetStats, ...],
    policy: OptimizerPolicy,
) -> dict[str, Decimal]:
    components = {
        "equal": _normalize_scores(_equal_scores(stats)),
        "inverse": _normalize_scores(_inverse_vol_scores(stats)),
        "risk": _normalize_scores(_risk_parity_scores(stats)),
        "kelly": _normalize_scores(_kelly_scores(stats, _d(policy.kelly_cap))),
    }
    weights = {
        "equal": _d(policy.dynamic_equal_weight),
        "inverse": _d(policy.dynamic_inverse_vol_weight),
        "risk": _d(policy.dynamic_risk_parity_weight),
        "kelly": _d(policy.dynamic_kelly_weight),
    }
    total = sum(weights.values(), ZERO)
    return {
        item.symbol: sum(
            components[name][item.symbol] * weights[name] / total
            for name in components
        )
        for item in stats
    }


def _cap_and_redistribute(
    raw_weights: Mapping[str, Decimal],
    invested_target: Decimal,
    max_weight: Decimal,
    min_weight: Decimal,
) -> dict[str, Decimal]:
    weights = {
        symbol: max(value * invested_target, ZERO)
        for symbol, value in _normalize_scores(raw_weights).items()
    }

    for _ in range(20):
        excess = ZERO
        uncapped = []
        for symbol, value in list(weights.items()):
            if value > max_weight:
                excess += value - max_weight
                weights[symbol] = max_weight
            else:
                uncapped.append(symbol)
        if excess <= Decimal("0.0000001") or not uncapped:
            break
        base = sum((weights[symbol] for symbol in uncapped), ZERO)
        if base <= ZERO:
            share = excess / Decimal(len(uncapped))
            for symbol in uncapped:
                weights[symbol] += share
        else:
            for symbol in uncapped:
                weights[symbol] += excess * (weights[symbol] / base)

    for symbol in list(weights):
        if ZERO < weights[symbol] < min_weight:
            weights[symbol] = ZERO

    current = sum(weights.values(), ZERO)
    if current > ZERO:
        scale = min(ONE, invested_target / current)
        weights = {symbol: value * scale for symbol, value in weights.items()}

    return {symbol: _q(value) for symbol, value in weights.items() if value > ZERO}


def optimize_portfolio(
    asset_stats: Iterable[AssetStats],
    policy: OptimizerPolicy | None = None,
) -> OptimizationResult:
    selected = policy or OptimizerPolicy()
    stats = _normalize_stats(asset_stats)
    stats = tuple(
        sorted(
            stats,
            key=lambda item: (
                item.expected_return * item.confidence / item.volatility,
                item.symbol,
            ),
            reverse=True,
        )[: selected.max_assets]
    )
    stats = tuple(sorted(stats, key=lambda item: item.symbol))

    method = selected.method.upper()
    if method == "EQUAL":
        scores = _equal_scores(stats)
    elif method == "INVERSE_VOL":
        scores = _inverse_vol_scores(stats)
    elif method == "RISK_PARITY":
        scores = _risk_parity_scores(stats)
    elif method == "KELLY":
        scores = _kelly_scores(stats, _d(selected.kelly_cap))
    else:
        scores = _blend_scores(stats, selected)

    invested_target = ONE - _d(selected.cash_reserve_pct)
    weights = _cap_and_redistribute(
        scores,
        invested_target,
        _d(selected.max_symbol_weight),
        _d(selected.min_symbol_weight),
    )
    invested = _q(sum(weights.values(), ZERO))
    cash = _q(ONE - invested)

    vol_map = {item.symbol: item.volatility for item in stats}
    score_map = _normalize_scores(scores)
    risk_total = sum(
        weights.get(symbol, ZERO) * vol_map[symbol]
        for symbol in weights
    )
    allocations = tuple(
        Allocation(
            symbol=symbol,
            weight=weights[symbol],
            method_score=_q(score_map[symbol]),
            risk_contribution=_q(
                weights[symbol] * vol_map[symbol] / risk_total
                if risk_total > ZERO else ZERO
            ),
        )
        for symbol in sorted(weights)
    )

    input_hash = _hash({
        "stats": [_stats_payload(item) for item in stats],
        "policy": _policy_payload(selected),
    })
    result = OptimizationResult(
        version=VERSION,
        method=method,
        invested_weight=invested,
        cash_weight=cash,
        allocations=allocations,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: OptimizationResult) -> bool:
    if result.version != VERSION:
        raise OptimizerError("unsupported result version")
    if result.method not in {"EQUAL", "INVERSE_VOL", "RISK_PARITY", "KELLY", "DYNAMIC"}:
        raise OptimizerError("invalid method")
    if result.invested_weight < ZERO or result.cash_weight < ZERO:
        raise OptimizerError("weights cannot be negative")
    if _q(result.invested_weight + result.cash_weight) != ONE.quantize(FOUR):
        raise OptimizerError("invested and cash weights must sum to 1")
    symbols = tuple(allocation.symbol for allocation in result.allocations)
    if symbols != tuple(sorted(symbols)) or len(symbols) != len(set(symbols)):
        raise OptimizerError("allocations must be unique and sorted")
    if _q(sum((a.weight for a in result.allocations), ZERO)) != result.invested_weight:
        raise OptimizerError("allocation weights do not match invested weight")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise OptimizerError("result hash mismatch")
    return True


def save_result(result: OptimizationResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> OptimizationResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    allocations = tuple(
        Allocation(
            symbol=item["symbol"],
            weight=_d(item["weight"]),
            method_score=_d(item["method_score"]),
            risk_contribution=_d(item["risk_contribution"]),
        )
        for item in payload["allocations"]
    )
    result = OptimizationResult(
        version=payload["version"],
        method=payload["method"],
        invested_weight=_d(payload["invested_weight"]),
        cash_weight=_d(payload["cash_weight"]),
        allocations=allocations,
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
