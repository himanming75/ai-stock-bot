from __future__ import annotations

"""
V29.2 Walk-Forward Validation Engine

Features:
- rolling and expanding walk-forward windows
- configurable train, test, and purge lengths
- deterministic candidate-parameter evaluation
- in-sample and out-of-sample metrics
- best-parameter selection per window
- stability and degradation analysis
- overfitting-risk score
- aggregate validation metrics
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety:
- completely offline
- no network, broker, market-data, account, order, or live execution access
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import sqrt
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
import json

VERSION = "29.2"
ZERO = Decimal("0")
ONE = Decimal("1")
Q = Decimal("0.000001")


class WalkForwardError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise WalkForwardError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise WalkForwardError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _mean(values: Sequence[Decimal]) -> Decimal:
    return ZERO if not values else sum(values, ZERO) / Decimal(len(values))


def _std(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return ZERO
    avg = _mean(values)
    variance = sum((x - avg) ** 2 for x in values) / Decimal(len(values))
    return _d(sqrt(float(variance)))


@dataclass(frozen=True)
class WalkForwardPolicy:
    train_size: int = 60
    test_size: int = 20
    purge_size: int = 0
    mode: str = "rolling"
    annualization_factor: int = 252
    minimum_windows: int = 2

    def __post_init__(self) -> None:
        if self.train_size < 2:
            raise WalkForwardError("train_size must be at least 2")
        if self.test_size < 1:
            raise WalkForwardError("test_size must be positive")
        if self.purge_size < 0:
            raise WalkForwardError("purge_size cannot be negative")
        if self.mode not in {"rolling", "expanding"}:
            raise WalkForwardError("mode must be rolling or expanding")
        if self.annualization_factor <= 0:
            raise WalkForwardError("annualization_factor must be positive")
        if self.minimum_windows < 1:
            raise WalkForwardError("minimum_windows must be positive")


@dataclass(frozen=True)
class ReturnObservation:
    timestamp: str
    value: Decimal


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    parameters: tuple[tuple[str, str], ...]
    in_sample_return_pct: Decimal
    in_sample_sharpe: Decimal
    in_sample_drawdown_pct: Decimal
    score: Decimal


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: str
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    selected_candidate_id: str
    selected_parameters: tuple[tuple[str, str], ...]
    candidate_scores: tuple[CandidateScore, ...]
    out_of_sample_return_pct: Decimal
    out_of_sample_sharpe: Decimal
    out_of_sample_drawdown_pct: Decimal
    degradation_pct: Decimal
    window_hash: str


@dataclass(frozen=True)
class WalkForwardMetrics:
    total_windows: int
    profitable_windows: int
    profitable_window_ratio: Decimal
    average_in_sample_return_pct: Decimal
    average_out_of_sample_return_pct: Decimal
    average_degradation_pct: Decimal
    out_of_sample_sharpe: Decimal
    out_of_sample_max_drawdown_pct: Decimal
    parameter_stability_ratio: Decimal
    overfitting_risk_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class WalkForwardResult:
    version: str
    validation_id: str
    policy: WalkForwardPolicy
    windows: tuple[WalkForwardWindow, ...]
    metrics: WalkForwardMetrics
    input_hash: str
    result_hash: str


def _policy_payload(policy: WalkForwardPolicy) -> dict[str, Any]:
    return {
        "train_size": policy.train_size,
        "test_size": policy.test_size,
        "purge_size": policy.purge_size,
        "mode": policy.mode,
        "annualization_factor": policy.annualization_factor,
        "minimum_windows": policy.minimum_windows,
    }


def _params_payload(params: tuple[tuple[str, str], ...]) -> list[list[str]]:
    return [[k, v] for k, v in params]


def _score_payload(item: CandidateScore) -> dict[str, Any]:
    return {
        "candidate_id": item.candidate_id,
        "parameters": _params_payload(item.parameters),
        "in_sample_return_pct": str(item.in_sample_return_pct),
        "in_sample_sharpe": str(item.in_sample_sharpe),
        "in_sample_drawdown_pct": str(item.in_sample_drawdown_pct),
        "score": str(item.score),
    }


def _window_payload(item: WalkForwardWindow, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "window_id": item.window_id,
        "train_start": item.train_start,
        "train_end": item.train_end,
        "test_start": item.test_start,
        "test_end": item.test_end,
        "selected_candidate_id": item.selected_candidate_id,
        "selected_parameters": _params_payload(item.selected_parameters),
        "candidate_scores": [_score_payload(x) for x in item.candidate_scores],
        "out_of_sample_return_pct": str(item.out_of_sample_return_pct),
        "out_of_sample_sharpe": str(item.out_of_sample_sharpe),
        "out_of_sample_drawdown_pct": str(item.out_of_sample_drawdown_pct),
        "degradation_pct": str(item.degradation_pct),
    }
    if include_hash:
        payload["window_hash"] = item.window_hash
    return payload


def _metrics_payload(item: WalkForwardMetrics) -> dict[str, Any]:
    return {
        "total_windows": item.total_windows,
        "profitable_windows": item.profitable_windows,
        "profitable_window_ratio": str(item.profitable_window_ratio),
        "average_in_sample_return_pct": str(item.average_in_sample_return_pct),
        "average_out_of_sample_return_pct": str(item.average_out_of_sample_return_pct),
        "average_degradation_pct": str(item.average_degradation_pct),
        "out_of_sample_sharpe": str(item.out_of_sample_sharpe),
        "out_of_sample_max_drawdown_pct": str(item.out_of_sample_max_drawdown_pct),
        "parameter_stability_ratio": str(item.parameter_stability_ratio),
        "overfitting_risk_score": str(item.overfitting_risk_score),
        "validation_passed": item.validation_passed,
    }


def _result_payload(result: WalkForwardResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "validation_id": result.validation_id,
        "policy": _policy_payload(result.policy),
        "windows": [_window_payload(x, include_hash=True) for x in result.windows],
        "metrics": _metrics_payload(result.metrics),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _normalize_params(params: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    if not params:
        raise WalkForwardError("candidate parameters cannot be empty")
    return tuple(sorted((str(k), str(v)) for k, v in params.items()))


def _performance(returns: Sequence[Decimal], annualization_factor: int) -> tuple[Decimal, Decimal, Decimal]:
    if not returns:
        return ZERO, ZERO, ZERO

    equity = ONE
    peak = ONE
    max_drawdown = ZERO
    for value in returns:
        if value <= Decimal("-1"):
            raise WalkForwardError("return cannot be less than or equal to -100%")
        equity *= ONE + value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - ONE)

    total_return = (equity - ONE) * Decimal("100")
    std = _std(returns)
    sharpe = ZERO if std == ZERO else _mean(returns) / std * _d(sqrt(annualization_factor))
    return _q(total_return), _q(sharpe), _q(max_drawdown * Decimal("100"))


def _candidate_id(params: tuple[tuple[str, str], ...]) -> str:
    return f"CAND-{_hash(_params_payload(params))[:12].upper()}"


def run_walk_forward_validation(
    observations: Iterable[ReturnObservation],
    candidates: Iterable[Mapping[str, Any]],
    evaluator: Callable[[tuple[ReturnObservation, ...], tuple[tuple[str, str], ...]], Sequence[Decimal]],
    policy: WalkForwardPolicy | None = None,
) -> WalkForwardResult:
    selected = policy or WalkForwardPolicy()
    data = tuple(observations)
    normalized_candidates = tuple(_normalize_params(x) for x in candidates)

    if len(data) < selected.train_size + selected.purge_size + selected.test_size:
        raise WalkForwardError("insufficient observations for one walk-forward window")
    if len(normalized_candidates) < 2:
        raise WalkForwardError("at least two candidates are required")
    if len(set(normalized_candidates)) != len(normalized_candidates):
        raise WalkForwardError("duplicate candidate parameters detected")

    previous_timestamp = None
    normalized_data = []
    for item in data:
        timestamp = item.timestamp.strip()
        if not timestamp:
            raise WalkForwardError("timestamp is required")
        if previous_timestamp is not None and timestamp <= previous_timestamp:
            raise WalkForwardError("timestamps must be strictly increasing")
        previous_timestamp = timestamp
        value = _q(item.value)
        if value <= Decimal("-1"):
            raise WalkForwardError("observation return cannot be <= -100%")
        normalized_data.append(ReturnObservation(timestamp, value))
    data = tuple(normalized_data)

    windows = []
    cursor = selected.train_size

    while cursor + selected.purge_size + selected.test_size <= len(data):
        train_start = 0 if selected.mode == "expanding" else cursor - selected.train_size
        train_end = cursor
        test_start = cursor + selected.purge_size
        test_end = test_start + selected.test_size

        train_slice = data[train_start:train_end]
        test_slice = data[test_start:test_end]

        scores = []
        candidate_returns: dict[str, tuple[Decimal, ...]] = {}

        for params in normalized_candidates:
            cid = _candidate_id(params)
            raw_returns = tuple(_q(x) for x in evaluator(train_slice, params))
            if len(raw_returns) != len(train_slice):
                raise WalkForwardError("evaluator must return one value per observation")
            train_return, train_sharpe, train_drawdown = _performance(
                raw_returns,
                selected.annualization_factor,
            )
            # Balanced selection score penalizes drawdown.
            score_value = train_return + train_sharpe * Decimal("5") + train_drawdown * Decimal("0.5")
            score = CandidateScore(
                candidate_id=cid,
                parameters=params,
                in_sample_return_pct=train_return,
                in_sample_sharpe=train_sharpe,
                in_sample_drawdown_pct=train_drawdown,
                score=_q(score_value),
            )
            scores.append(score)
            candidate_returns[cid] = raw_returns

        ranked = tuple(sorted(scores, key=lambda x: (x.score, x.candidate_id), reverse=True))
        best = ranked[0]

        test_returns = tuple(_q(x) for x in evaluator(test_slice, best.parameters))
        if len(test_returns) != len(test_slice):
            raise WalkForwardError("evaluator must return one value per observation")
        test_return, test_sharpe, test_drawdown = _performance(
            test_returns,
            selected.annualization_factor,
        )

        if best.in_sample_return_pct == ZERO:
            degradation = ZERO
        else:
            degradation = (
                (test_return - best.in_sample_return_pct)
                / abs(best.in_sample_return_pct)
                * Decimal("100")
            )

        window_seed = {
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "selected_candidate_id": best.candidate_id,
        }
        window = WalkForwardWindow(
            window_id=f"WF-{_hash(window_seed)[:12].upper()}",
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            selected_candidate_id=best.candidate_id,
            selected_parameters=best.parameters,
            candidate_scores=ranked,
            out_of_sample_return_pct=test_return,
            out_of_sample_sharpe=test_sharpe,
            out_of_sample_drawdown_pct=test_drawdown,
            degradation_pct=_q(degradation),
            window_hash="",
        )
        window = replace(window, window_hash=_hash(_window_payload(window)))
        windows.append(window)
        cursor += selected.test_size

    if len(windows) < selected.minimum_windows:
        raise WalkForwardError("minimum walk-forward window count was not reached")

    in_sample_returns = [w.candidate_scores[0].in_sample_return_pct for w in windows]
    out_sample_returns = [w.out_of_sample_return_pct for w in windows]
    degradations = [w.degradation_pct for w in windows]
    profitable = sum(1 for x in out_sample_returns if x > ZERO)
    selected_ids = [w.selected_candidate_id for w in windows]
    most_common_count = max(selected_ids.count(x) for x in set(selected_ids))
    parameter_stability = Decimal(most_common_count) / Decimal(len(selected_ids))

    # Aggregate OOS returns at window level.
    oos_fractional = [x / Decimal("100") for x in out_sample_returns]
    _, aggregate_sharpe, aggregate_drawdown = _performance(
        oos_fractional,
        selected.annualization_factor,
    )

    positive_degradation_penalty = _mean([max(-x, ZERO) for x in degradations])
    unprofitable_penalty = (ONE - Decimal(profitable) / Decimal(len(windows))) * Decimal("100")
    instability_penalty = (ONE - parameter_stability) * Decimal("100")
    overfitting_risk = min(
        Decimal("100"),
        positive_degradation_penalty * Decimal("0.5")
        + unprofitable_penalty * Decimal("0.3")
        + instability_penalty * Decimal("0.2"),
    )

    validation_passed = (
        profitable / len(windows) >= 0.5
        and _mean(out_sample_returns) > ZERO
        and overfitting_risk < Decimal("70")
    )

    metrics = WalkForwardMetrics(
        total_windows=len(windows),
        profitable_windows=profitable,
        profitable_window_ratio=_q(Decimal(profitable) / Decimal(len(windows))),
        average_in_sample_return_pct=_q(_mean(in_sample_returns)),
        average_out_of_sample_return_pct=_q(_mean(out_sample_returns)),
        average_degradation_pct=_q(_mean(degradations)),
        out_of_sample_sharpe=_q(aggregate_sharpe),
        out_of_sample_max_drawdown_pct=_q(aggregate_drawdown),
        parameter_stability_ratio=_q(parameter_stability),
        overfitting_risk_score=_q(overfitting_risk),
        validation_passed=validation_passed,
    )

    input_hash = _hash({
        "policy": _policy_payload(selected),
        "observations": [{"timestamp": x.timestamp, "value": str(x.value)} for x in data],
        "candidates": [_params_payload(x) for x in normalized_candidates],
    })

    result = WalkForwardResult(
        version=VERSION,
        validation_id=f"WFV-{input_hash[:16].upper()}",
        policy=selected,
        windows=tuple(windows),
        metrics=metrics,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_window(window: WalkForwardWindow) -> bool:
    if window.train_start < 0 or window.train_end <= window.train_start:
        raise WalkForwardError("invalid training window")
    if window.test_start < window.train_end or window.test_end <= window.test_start:
        raise WalkForwardError("invalid test window")
    if not window.candidate_scores:
        raise WalkForwardError("candidate scores cannot be empty")
    if window.selected_candidate_id != window.candidate_scores[0].candidate_id:
        raise WalkForwardError("selected candidate mismatch")
    clean = replace(window, window_hash="")
    if window.window_hash != _hash(_window_payload(clean)):
        raise WalkForwardError("window hash mismatch")
    return True


def verify_result(result: WalkForwardResult) -> bool:
    if result.version != VERSION:
        raise WalkForwardError("unsupported version")
    if not result.validation_id.startswith("WFV-"):
        raise WalkForwardError("invalid validation ID")
    if result.metrics.total_windows != len(result.windows):
        raise WalkForwardError("window count mismatch")
    for window in result.windows:
        verify_window(window)
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise WalkForwardError("result hash mismatch")
    return True


def save_result(result: WalkForwardResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> WalkForwardResult:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    pol = p["policy"]
    policy = WalkForwardPolicy(
        train_size=int(pol["train_size"]),
        test_size=int(pol["test_size"]),
        purge_size=int(pol["purge_size"]),
        mode=pol["mode"],
        annualization_factor=int(pol["annualization_factor"]),
        minimum_windows=int(pol["minimum_windows"]),
    )

    windows = []
    for w in p["windows"]:
        candidate_scores = tuple(
            CandidateScore(
                candidate_id=x["candidate_id"],
                parameters=tuple((str(a), str(b)) for a, b in x["parameters"]),
                in_sample_return_pct=_d(x["in_sample_return_pct"]),
                in_sample_sharpe=_d(x["in_sample_sharpe"]),
                in_sample_drawdown_pct=_d(x["in_sample_drawdown_pct"]),
                score=_d(x["score"]),
            )
            for x in w["candidate_scores"]
        )
        windows.append(WalkForwardWindow(
            window_id=w["window_id"],
            train_start=int(w["train_start"]),
            train_end=int(w["train_end"]),
            test_start=int(w["test_start"]),
            test_end=int(w["test_end"]),
            selected_candidate_id=w["selected_candidate_id"],
            selected_parameters=tuple((str(a), str(b)) for a, b in w["selected_parameters"]),
            candidate_scores=candidate_scores,
            out_of_sample_return_pct=_d(w["out_of_sample_return_pct"]),
            out_of_sample_sharpe=_d(w["out_of_sample_sharpe"]),
            out_of_sample_drawdown_pct=_d(w["out_of_sample_drawdown_pct"]),
            degradation_pct=_d(w["degradation_pct"]),
            window_hash=w["window_hash"],
        ))

    m = p["metrics"]
    metrics = WalkForwardMetrics(
        total_windows=int(m["total_windows"]),
        profitable_windows=int(m["profitable_windows"]),
        profitable_window_ratio=_d(m["profitable_window_ratio"]),
        average_in_sample_return_pct=_d(m["average_in_sample_return_pct"]),
        average_out_of_sample_return_pct=_d(m["average_out_of_sample_return_pct"]),
        average_degradation_pct=_d(m["average_degradation_pct"]),
        out_of_sample_sharpe=_d(m["out_of_sample_sharpe"]),
        out_of_sample_max_drawdown_pct=_d(m["out_of_sample_max_drawdown_pct"]),
        parameter_stability_ratio=_d(m["parameter_stability_ratio"]),
        overfitting_risk_score=_d(m["overfitting_risk_score"]),
        validation_passed=bool(m["validation_passed"]),
    )

    result = WalkForwardResult(
        version=p["version"],
        validation_id=p["validation_id"],
        policy=policy,
        windows=tuple(windows),
        metrics=metrics,
        input_hash=p["input_hash"],
        result_hash=p["result_hash"],
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
