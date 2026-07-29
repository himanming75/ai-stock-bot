from __future__ import annotations

"""
V26.6 Offline Walk-Forward Validation Engine

Features:
- rolling and expanding training windows
- out-of-sample validation windows
- configurable step size and purge gap
- deterministic parameter selection from training scores
- fold-level train/test metrics
- efficiency, stability, degradation, pass/fail evaluation
- aggregate walk-forward statistics
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence
import json

VERSION = "26.6"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


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
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ParameterResult:
    parameter_id: str
    train_score: Decimal
    train_return_pct: Decimal
    train_drawdown_pct: Decimal
    test_return_pct: Decimal
    test_drawdown_pct: Decimal


@dataclass(frozen=True)
class WalkForwardPolicy:
    train_size: int = 120
    test_size: int = 30
    step_size: int = 30
    purge_size: int = 0
    mode: str = "ROLLING"
    min_train_score: Decimal = Decimal("0")
    min_test_return_pct: Decimal = Decimal("-5")
    max_test_drawdown_pct: Decimal = Decimal("-20")
    min_efficiency_pct: Decimal = Decimal("0")
    max_degradation_pct: Decimal = Decimal("100")

    def __post_init__(self) -> None:
        if self.train_size <= 0 or self.test_size <= 0 or self.step_size <= 0:
            raise WalkForwardError("window sizes and step size must be positive")
        if self.purge_size < 0:
            raise WalkForwardError("purge size cannot be negative")
        if self.mode.upper() not in {"ROLLING", "EXPANDING"}:
            raise WalkForwardError("mode must be ROLLING or EXPANDING")
        if _d(self.max_test_drawdown_pct) > ZERO:
            raise WalkForwardError("maximum test drawdown must be zero or negative")
        if _d(self.min_efficiency_pct) < Decimal("-1000"):
            raise WalkForwardError("invalid minimum efficiency")
        if _d(self.max_degradation_pct) < ZERO:
            raise WalkForwardError("maximum degradation cannot be negative")


@dataclass(frozen=True)
class FoldWindow:
    fold_index: int
    train_start: int
    train_end: int
    purge_start: int
    purge_end: int
    test_start: int
    test_end: int
    fold_hash: str


@dataclass(frozen=True)
class FoldResult:
    fold_index: int
    window: FoldWindow
    selected_parameter_id: str
    train_score: Decimal
    train_return_pct: Decimal
    train_drawdown_pct: Decimal
    test_return_pct: Decimal
    test_drawdown_pct: Decimal
    efficiency_pct: Decimal
    degradation_pct: Decimal
    passed: bool
    reason_codes: tuple[str, ...]
    result_hash: str


@dataclass(frozen=True)
class WalkForwardResult:
    version: str
    mode: str
    data_length: int
    total_folds: int
    passed_folds: int
    failed_folds: int
    pass_rate_pct: Decimal
    average_train_return_pct: Decimal
    average_test_return_pct: Decimal
    average_efficiency_pct: Decimal
    average_degradation_pct: Decimal
    test_return_stability: Decimal
    cumulative_test_return_pct: Decimal
    folds: tuple[FoldResult, ...]
    input_hash: str
    result_hash: str


def _parameter_payload(item: ParameterResult) -> dict[str, str]:
    return {
        "parameter_id": item.parameter_id,
        "train_score": str(item.train_score),
        "train_return_pct": str(item.train_return_pct),
        "train_drawdown_pct": str(item.train_drawdown_pct),
        "test_return_pct": str(item.test_return_pct),
        "test_drawdown_pct": str(item.test_drawdown_pct),
    }


def _window_payload(window: FoldWindow, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "fold_index": window.fold_index,
        "train_start": window.train_start,
        "train_end": window.train_end,
        "purge_start": window.purge_start,
        "purge_end": window.purge_end,
        "test_start": window.test_start,
        "test_end": window.test_end,
    }
    if include_hash:
        payload["fold_hash"] = window.fold_hash
    return payload


def _fold_payload(fold: FoldResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "fold_index": fold.fold_index,
        "window": _window_payload(fold.window, include_hash=True),
        "selected_parameter_id": fold.selected_parameter_id,
        "train_score": str(fold.train_score),
        "train_return_pct": str(fold.train_return_pct),
        "train_drawdown_pct": str(fold.train_drawdown_pct),
        "test_return_pct": str(fold.test_return_pct),
        "test_drawdown_pct": str(fold.test_drawdown_pct),
        "efficiency_pct": str(fold.efficiency_pct),
        "degradation_pct": str(fold.degradation_pct),
        "passed": fold.passed,
        "reason_codes": list(fold.reason_codes),
    }
    if include_hash:
        payload["result_hash"] = fold.result_hash
    return payload


def _result_payload(result: WalkForwardResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "mode": result.mode,
        "data_length": result.data_length,
        "total_folds": result.total_folds,
        "passed_folds": result.passed_folds,
        "failed_folds": result.failed_folds,
        "pass_rate_pct": str(result.pass_rate_pct),
        "average_train_return_pct": str(result.average_train_return_pct),
        "average_test_return_pct": str(result.average_test_return_pct),
        "average_efficiency_pct": str(result.average_efficiency_pct),
        "average_degradation_pct": str(result.average_degradation_pct),
        "test_return_stability": str(result.test_return_stability),
        "cumulative_test_return_pct": str(result.cumulative_test_return_pct),
        "folds": [_fold_payload(fold, include_hash=True) for fold in result.folds],
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def create_windows(data_length: int, policy: WalkForwardPolicy) -> tuple[FoldWindow, ...]:
    if data_length <= 0:
        raise WalkForwardError("data length must be positive")

    mode = policy.mode.upper()
    windows: list[FoldWindow] = []
    fold_index = 0
    anchor = policy.train_size

    while True:
        if mode == "ROLLING":
            train_start = anchor - policy.train_size
        else:
            train_start = 0

        train_end = anchor
        purge_start = train_end
        purge_end = purge_start + policy.purge_size
        test_start = purge_end
        test_end = test_start + policy.test_size

        if test_end > data_length:
            break

        window = FoldWindow(
            fold_index=fold_index,
            train_start=train_start,
            train_end=train_end,
            purge_start=purge_start,
            purge_end=purge_end,
            test_start=test_start,
            test_end=test_end,
            fold_hash="",
        )
        window = replace(window, fold_hash=_hash(_window_payload(window)))
        windows.append(window)

        fold_index += 1
        anchor += policy.step_size

    if not windows:
        raise WalkForwardError("insufficient data for one walk-forward fold")
    return tuple(windows)


def verify_window(window: FoldWindow) -> bool:
    if window.fold_index < 0:
        raise WalkForwardError("fold index cannot be negative")
    if not (
        0 <= window.train_start < window.train_end
        <= window.purge_start <= window.purge_end
        <= window.test_start < window.test_end
    ):
        raise WalkForwardError("invalid fold window boundaries")
    clean = replace(window, fold_hash="")
    if window.fold_hash != _hash(_window_payload(clean)):
        raise WalkForwardError("fold window hash mismatch")
    return True


def _normalize_parameter(item: ParameterResult) -> ParameterResult:
    parameter_id = item.parameter_id.strip()
    if not parameter_id:
        raise WalkForwardError("parameter ID is required")
    train_drawdown = _q(item.train_drawdown_pct)
    test_drawdown = _q(item.test_drawdown_pct)
    if train_drawdown > ZERO or test_drawdown > ZERO:
        raise WalkForwardError("drawdown values must be zero or negative")
    return ParameterResult(
        parameter_id=parameter_id,
        train_score=_q(item.train_score),
        train_return_pct=_q(item.train_return_pct),
        train_drawdown_pct=train_drawdown,
        test_return_pct=_q(item.test_return_pct),
        test_drawdown_pct=test_drawdown,
    )


def evaluate_fold(
    window: FoldWindow,
    parameter_results: Iterable[ParameterResult],
    policy: WalkForwardPolicy,
) -> FoldResult:
    verify_window(window)
    parameters = tuple(sorted(
        (_normalize_parameter(item) for item in parameter_results),
        key=lambda item: item.parameter_id,
    ))
    if not parameters:
        raise WalkForwardError("parameter results cannot be empty")
    if len({item.parameter_id for item in parameters}) != len(parameters):
        raise WalkForwardError("duplicate parameter IDs detected")

    selected = max(
        parameters,
        key=lambda item: (
            item.train_score,
            item.train_return_pct,
            item.train_drawdown_pct,
            item.parameter_id,
        ),
    )

    if selected.train_return_pct == ZERO:
        efficiency = ZERO if selected.test_return_pct == ZERO else Decimal("-999.0000")
    else:
        efficiency = _q(
            selected.test_return_pct / abs(selected.train_return_pct) * Decimal("100")
        )

    denominator = max(abs(selected.train_return_pct), Decimal("0.0001"))
    degradation = _q(
        max(selected.train_return_pct - selected.test_return_pct, ZERO)
        / denominator
        * Decimal("100")
    )

    reasons: list[str] = []
    if selected.train_score < _d(policy.min_train_score):
        reasons.append("LOW_TRAIN_SCORE")
    if selected.test_return_pct < _d(policy.min_test_return_pct):
        reasons.append("LOW_TEST_RETURN")
    if selected.test_drawdown_pct < _d(policy.max_test_drawdown_pct):
        reasons.append("EXCESSIVE_TEST_DRAWDOWN")
    if efficiency < _d(policy.min_efficiency_pct):
        reasons.append("LOW_EFFICIENCY")
    if degradation > _d(policy.max_degradation_pct):
        reasons.append("EXCESSIVE_DEGRADATION")

    fold = FoldResult(
        fold_index=window.fold_index,
        window=window,
        selected_parameter_id=selected.parameter_id,
        train_score=selected.train_score,
        train_return_pct=selected.train_return_pct,
        train_drawdown_pct=selected.train_drawdown_pct,
        test_return_pct=selected.test_return_pct,
        test_drawdown_pct=selected.test_drawdown_pct,
        efficiency_pct=efficiency,
        degradation_pct=degradation,
        passed=not reasons,
        reason_codes=tuple(sorted(reasons)),
        result_hash="",
    )
    return replace(fold, result_hash=_hash(_fold_payload(fold)))


def verify_fold(fold: FoldResult) -> bool:
    verify_window(fold.window)
    if fold.fold_index != fold.window.fold_index:
        raise WalkForwardError("fold index mismatch")
    if fold.passed and fold.reason_codes:
        raise WalkForwardError("passed fold cannot contain failure reasons")
    if not fold.passed and not fold.reason_codes:
        raise WalkForwardError("failed fold must contain reasons")
    if fold.train_drawdown_pct > ZERO or fold.test_drawdown_pct > ZERO:
        raise WalkForwardError("drawdown values cannot be positive")
    clean = replace(fold, result_hash="")
    if fold.result_hash != _hash(_fold_payload(clean)):
        raise WalkForwardError("fold result hash mismatch")
    return True


def run_walk_forward(
    data_length: int,
    fold_parameter_results: Mapping[int, Sequence[ParameterResult]],
    policy: WalkForwardPolicy | None = None,
) -> WalkForwardResult:
    selected = policy or WalkForwardPolicy()
    windows = create_windows(data_length, selected)

    extra_indices = set(fold_parameter_results) - {window.fold_index for window in windows}
    if extra_indices:
        raise WalkForwardError("parameter results contain unknown fold indices")

    folds: list[FoldResult] = []
    for window in windows:
        if window.fold_index not in fold_parameter_results:
            raise WalkForwardError(f"missing parameter results for fold {window.fold_index}")
        folds.append(evaluate_fold(
            window,
            fold_parameter_results[window.fold_index],
            selected,
        ))

    passed = sum(1 for fold in folds if fold.passed)
    failed = len(folds) - passed
    avg_train = mean([float(fold.train_return_pct) for fold in folds])
    avg_test = mean([float(fold.test_return_pct) for fold in folds])
    avg_efficiency = mean([float(fold.efficiency_pct) for fold in folds])
    avg_degradation = mean([float(fold.degradation_pct) for fold in folds])
    stability = pstdev([float(fold.test_return_pct) for fold in folds]) if len(folds) > 1 else 0.0

    growth = Decimal("1")
    for fold in folds:
        growth *= Decimal("1") + fold.test_return_pct / Decimal("100")
    cumulative = (growth - Decimal("1")) * Decimal("100")

    input_hash = _hash({
        "data_length": data_length,
        "policy": {
            "train_size": selected.train_size,
            "test_size": selected.test_size,
            "step_size": selected.step_size,
            "purge_size": selected.purge_size,
            "mode": selected.mode.upper(),
            "min_train_score": str(selected.min_train_score),
            "min_test_return_pct": str(selected.min_test_return_pct),
            "max_test_drawdown_pct": str(selected.max_test_drawdown_pct),
            "min_efficiency_pct": str(selected.min_efficiency_pct),
            "max_degradation_pct": str(selected.max_degradation_pct),
        },
        "fold_parameter_results": {
            str(index): [_parameter_payload(_normalize_parameter(item)) for item in results]
            for index, results in sorted(fold_parameter_results.items())
        },
    })

    result = WalkForwardResult(
        version=VERSION,
        mode=selected.mode.upper(),
        data_length=data_length,
        total_folds=len(folds),
        passed_folds=passed,
        failed_folds=failed,
        pass_rate_pct=_q(Decimal(passed) / Decimal(len(folds)) * Decimal("100")),
        average_train_return_pct=_q(avg_train),
        average_test_return_pct=_q(avg_test),
        average_efficiency_pct=_q(avg_efficiency),
        average_degradation_pct=_q(avg_degradation),
        test_return_stability=_q(stability),
        cumulative_test_return_pct=_q(cumulative),
        folds=tuple(folds),
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_result(result: WalkForwardResult) -> bool:
    if result.version != VERSION:
        raise WalkForwardError("unsupported result version")
    if result.mode not in {"ROLLING", "EXPANDING"}:
        raise WalkForwardError("invalid result mode")
    if result.total_folds != len(result.folds):
        raise WalkForwardError("fold count mismatch")
    if result.passed_folds + result.failed_folds != result.total_folds:
        raise WalkForwardError("pass/fail count mismatch")
    if result.pass_rate_pct < ZERO or result.pass_rate_pct > Decimal("100"):
        raise WalkForwardError("pass rate out of range")
    for expected, fold in enumerate(result.folds):
        verify_fold(fold)
        if fold.fold_index != expected:
            raise WalkForwardError("fold order is invalid")
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise WalkForwardError("walk-forward result hash mismatch")
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
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    folds = []
    for item in payload["folds"]:
        window_data = item["window"]
        window = FoldWindow(
            fold_index=int(window_data["fold_index"]),
            train_start=int(window_data["train_start"]),
            train_end=int(window_data["train_end"]),
            purge_start=int(window_data["purge_start"]),
            purge_end=int(window_data["purge_end"]),
            test_start=int(window_data["test_start"]),
            test_end=int(window_data["test_end"]),
            fold_hash=window_data["fold_hash"],
        )
        folds.append(FoldResult(
            fold_index=int(item["fold_index"]),
            window=window,
            selected_parameter_id=item["selected_parameter_id"],
            train_score=_d(item["train_score"]),
            train_return_pct=_d(item["train_return_pct"]),
            train_drawdown_pct=_d(item["train_drawdown_pct"]),
            test_return_pct=_d(item["test_return_pct"]),
            test_drawdown_pct=_d(item["test_drawdown_pct"]),
            efficiency_pct=_d(item["efficiency_pct"]),
            degradation_pct=_d(item["degradation_pct"]),
            passed=bool(item["passed"]),
            reason_codes=tuple(item["reason_codes"]),
            result_hash=item["result_hash"],
        ))

    result = WalkForwardResult(
        version=payload["version"],
        mode=payload["mode"],
        data_length=int(payload["data_length"]),
        total_folds=int(payload["total_folds"]),
        passed_folds=int(payload["passed_folds"]),
        failed_folds=int(payload["failed_folds"]),
        pass_rate_pct=_d(payload["pass_rate_pct"]),
        average_train_return_pct=_d(payload["average_train_return_pct"]),
        average_test_return_pct=_d(payload["average_test_return_pct"]),
        average_efficiency_pct=_d(payload["average_efficiency_pct"]),
        average_degradation_pct=_d(payload["average_degradation_pct"]),
        test_return_stability=_d(payload["test_return_stability"]),
        cumulative_test_return_pct=_d(payload["cumulative_test_return_pct"]),
        folds=tuple(folds),
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
