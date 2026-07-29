from __future__ import annotations

"""
V29.3 Monte Carlo & Robustness Analysis

Features:
- deterministic bootstrap Monte Carlo simulation
- deterministic shuffled-sequence simulation
- configurable simulation count and random seed
- terminal-return distribution
- maximum-drawdown distribution
- loss probability and ruin probability
- percentile analysis
- Value at Risk and Conditional Value at Risk
- robustness score and validation decision
- SHA-256 integrity verification
- JSON persistence and tamper detection

Safety:
- completely offline
- no network, broker, market-data, account, order, or live execution access
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from random import Random
from typing import Any, Iterable, Sequence
import json

VERSION = "29.3"
ZERO = Decimal("0")
ONE = Decimal("1")
Q = Decimal("0.000001")


class MonteCarloError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise MonteCarloError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise MonteCarloError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _mean(values: Sequence[Decimal]) -> Decimal:
    return ZERO if not values else sum(values, ZERO) / Decimal(len(values))


def _percentile(values: Sequence[Decimal], percentile: Decimal) -> Decimal:
    if not values:
        raise MonteCarloError("percentile requires data")
    ordered = sorted(values)
    p = max(ZERO, min(ONE, percentile))
    index = int((len(ordered) - 1) * float(p))
    return ordered[index]


@dataclass(frozen=True)
class MonteCarloPolicy:
    simulations: int = 1000
    seed: int = 2903
    mode: str = "bootstrap"
    ruin_threshold_pct: Decimal = Decimal("-50")
    confidence_level: Decimal = Decimal("0.95")
    minimum_robustness_score: Decimal = Decimal("60")

    def __post_init__(self) -> None:
        if self.simulations < 100:
            raise MonteCarloError("simulations must be at least 100")
        if self.mode not in {"bootstrap", "shuffle"}:
            raise MonteCarloError("mode must be bootstrap or shuffle")
        if _d(self.ruin_threshold_pct) >= ZERO:
            raise MonteCarloError("ruin_threshold_pct must be negative")
        confidence = _d(self.confidence_level)
        if confidence <= Decimal("0.5") or confidence >= ONE:
            raise MonteCarloError("confidence_level must be between 0.5 and 1")
        score = _d(self.minimum_robustness_score)
        if score < ZERO or score > Decimal("100"):
            raise MonteCarloError("minimum_robustness_score must be between 0 and 100")


@dataclass(frozen=True)
class SimulationPath:
    simulation_id: str
    terminal_return_pct: Decimal
    max_drawdown_pct: Decimal
    ruined: bool
    path_hash: str


@dataclass(frozen=True)
class MonteCarloMetrics:
    simulation_count: int
    mean_terminal_return_pct: Decimal
    median_terminal_return_pct: Decimal
    percentile_5_return_pct: Decimal
    percentile_25_return_pct: Decimal
    percentile_75_return_pct: Decimal
    percentile_95_return_pct: Decimal
    worst_terminal_return_pct: Decimal
    best_terminal_return_pct: Decimal
    mean_max_drawdown_pct: Decimal
    worst_max_drawdown_pct: Decimal
    loss_probability: Decimal
    ruin_probability: Decimal
    value_at_risk_pct: Decimal
    conditional_value_at_risk_pct: Decimal
    robustness_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class MonteCarloResult:
    version: str
    analysis_id: str
    policy: MonteCarloPolicy
    source_return_count: int
    paths: tuple[SimulationPath, ...]
    metrics: MonteCarloMetrics
    input_hash: str
    result_hash: str


def _policy_payload(policy: MonteCarloPolicy) -> dict[str, Any]:
    return {
        "simulations": policy.simulations,
        "seed": policy.seed,
        "mode": policy.mode,
        "ruin_threshold_pct": str(policy.ruin_threshold_pct),
        "confidence_level": str(policy.confidence_level),
        "minimum_robustness_score": str(policy.minimum_robustness_score),
    }


def _path_payload(path: SimulationPath, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "simulation_id": path.simulation_id,
        "terminal_return_pct": str(path.terminal_return_pct),
        "max_drawdown_pct": str(path.max_drawdown_pct),
        "ruined": path.ruined,
    }
    if include_hash:
        payload["path_hash"] = path.path_hash
    return payload


def _metrics_payload(metrics: MonteCarloMetrics) -> dict[str, Any]:
    return {
        "simulation_count": metrics.simulation_count,
        "mean_terminal_return_pct": str(metrics.mean_terminal_return_pct),
        "median_terminal_return_pct": str(metrics.median_terminal_return_pct),
        "percentile_5_return_pct": str(metrics.percentile_5_return_pct),
        "percentile_25_return_pct": str(metrics.percentile_25_return_pct),
        "percentile_75_return_pct": str(metrics.percentile_75_return_pct),
        "percentile_95_return_pct": str(metrics.percentile_95_return_pct),
        "worst_terminal_return_pct": str(metrics.worst_terminal_return_pct),
        "best_terminal_return_pct": str(metrics.best_terminal_return_pct),
        "mean_max_drawdown_pct": str(metrics.mean_max_drawdown_pct),
        "worst_max_drawdown_pct": str(metrics.worst_max_drawdown_pct),
        "loss_probability": str(metrics.loss_probability),
        "ruin_probability": str(metrics.ruin_probability),
        "value_at_risk_pct": str(metrics.value_at_risk_pct),
        "conditional_value_at_risk_pct": str(metrics.conditional_value_at_risk_pct),
        "robustness_score": str(metrics.robustness_score),
        "validation_passed": metrics.validation_passed,
    }


def _result_payload(result: MonteCarloResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "analysis_id": result.analysis_id,
        "policy": _policy_payload(result.policy),
        "source_return_count": result.source_return_count,
        "paths": [_path_payload(path, include_hash=True) for path in result.paths],
        "metrics": _metrics_payload(result.metrics),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _simulate_path(returns: Sequence[Decimal]) -> tuple[Decimal, Decimal]:
    equity = ONE
    peak = ONE
    maximum_drawdown = ZERO

    for value in returns:
        if value <= Decimal("-1"):
            raise MonteCarloError("return cannot be less than or equal to -100%")
        equity *= ONE + value
        if equity > peak:
            peak = equity
        drawdown = equity / peak - ONE
        maximum_drawdown = min(maximum_drawdown, drawdown)

    return (
        _q((equity - ONE) * Decimal("100")),
        _q(maximum_drawdown * Decimal("100")),
    )


def analyze_monte_carlo(
    returns: Iterable[Any],
    policy: MonteCarloPolicy | None = None,
) -> MonteCarloResult:
    selected = policy or MonteCarloPolicy()
    normalized = tuple(_q(value) for value in returns)

    if len(normalized) < 10:
        raise MonteCarloError("at least ten returns are required")
    if any(value <= Decimal("-1") for value in normalized):
        raise MonteCarloError("return cannot be less than or equal to -100%")

    rng = Random(selected.seed)
    paths = []

    for index in range(selected.simulations):
        if selected.mode == "bootstrap":
            simulated = tuple(normalized[rng.randrange(len(normalized))] for _ in normalized)
        else:
            shuffled = list(normalized)
            rng.shuffle(shuffled)
            simulated = tuple(shuffled)

        terminal, drawdown = _simulate_path(simulated)
        ruined = drawdown <= _d(selected.ruin_threshold_pct)

        path = SimulationPath(
            simulation_id=f"MC-{index + 1:06d}",
            terminal_return_pct=terminal,
            max_drawdown_pct=drawdown,
            ruined=ruined,
            path_hash="",
        )
        path = replace(path, path_hash=_hash(_path_payload(path)))
        paths.append(path)

    terminal_returns = [path.terminal_return_pct for path in paths]
    drawdowns = [path.max_drawdown_pct for path in paths]

    loss_probability = Decimal(sum(1 for value in terminal_returns if value < ZERO)) / Decimal(len(paths))
    ruin_probability = Decimal(sum(1 for path in paths if path.ruined)) / Decimal(len(paths))

    tail_probability = ONE - _d(selected.confidence_level)
    var_value = _percentile(terminal_returns, tail_probability)
    tail_values = [value for value in terminal_returns if value <= var_value]
    cvar_value = _mean(tail_values)

    loss_penalty = loss_probability * Decimal("40")
    ruin_penalty = ruin_probability * Decimal("40")
    drawdown_penalty = min(Decimal("20"), abs(_mean(drawdowns)) * Decimal("0.4"))
    robustness_score = max(
        ZERO,
        Decimal("100") - loss_penalty - ruin_penalty - drawdown_penalty,
    )

    metrics = MonteCarloMetrics(
        simulation_count=len(paths),
        mean_terminal_return_pct=_q(_mean(terminal_returns)),
        median_terminal_return_pct=_q(_percentile(terminal_returns, Decimal("0.50"))),
        percentile_5_return_pct=_q(_percentile(terminal_returns, Decimal("0.05"))),
        percentile_25_return_pct=_q(_percentile(terminal_returns, Decimal("0.25"))),
        percentile_75_return_pct=_q(_percentile(terminal_returns, Decimal("0.75"))),
        percentile_95_return_pct=_q(_percentile(terminal_returns, Decimal("0.95"))),
        worst_terminal_return_pct=_q(min(terminal_returns)),
        best_terminal_return_pct=_q(max(terminal_returns)),
        mean_max_drawdown_pct=_q(_mean(drawdowns)),
        worst_max_drawdown_pct=_q(min(drawdowns)),
        loss_probability=_q(loss_probability),
        ruin_probability=_q(ruin_probability),
        value_at_risk_pct=_q(var_value),
        conditional_value_at_risk_pct=_q(cvar_value),
        robustness_score=_q(robustness_score),
        validation_passed=(
            robustness_score >= _d(selected.minimum_robustness_score)
            and ruin_probability <= Decimal("0.10")
            and _percentile(terminal_returns, Decimal("0.05")) > _d(selected.ruin_threshold_pct)
        ),
    )

    input_hash = _hash({
        "returns": [str(value) for value in normalized],
        "policy": _policy_payload(selected),
    })

    result = MonteCarloResult(
        version=VERSION,
        analysis_id=f"MCR-{input_hash[:16].upper()}",
        policy=selected,
        source_return_count=len(normalized),
        paths=tuple(paths),
        metrics=metrics,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_path(path: SimulationPath) -> bool:
    if not path.simulation_id.startswith("MC-"):
        raise MonteCarloError("invalid simulation ID")
    if path.max_drawdown_pct > ZERO:
        raise MonteCarloError("maximum drawdown cannot be positive")
    clean = replace(path, path_hash="")
    if path.path_hash != _hash(_path_payload(clean)):
        raise MonteCarloError("simulation path hash mismatch")
    return True


def verify_result(result: MonteCarloResult) -> bool:
    if result.version != VERSION:
        raise MonteCarloError("unsupported version")
    if not result.analysis_id.startswith("MCR-"):
        raise MonteCarloError("invalid analysis ID")
    if result.metrics.simulation_count != len(result.paths):
        raise MonteCarloError("simulation count mismatch")
    if result.source_return_count < 10:
        raise MonteCarloError("invalid source return count")
    if result.metrics.loss_probability < ZERO or result.metrics.loss_probability > ONE:
        raise MonteCarloError("invalid loss probability")
    if result.metrics.ruin_probability < ZERO or result.metrics.ruin_probability > ONE:
        raise MonteCarloError("invalid ruin probability")
    if result.metrics.robustness_score < ZERO or result.metrics.robustness_score > Decimal("100"):
        raise MonteCarloError("invalid robustness score")
    for path in result.paths:
        verify_path(path)
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise MonteCarloError("result hash mismatch")
    return True


def save_result(result: MonteCarloResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> MonteCarloResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    pol = payload["policy"]
    policy = MonteCarloPolicy(
        simulations=int(pol["simulations"]),
        seed=int(pol["seed"]),
        mode=pol["mode"],
        ruin_threshold_pct=_d(pol["ruin_threshold_pct"]),
        confidence_level=_d(pol["confidence_level"]),
        minimum_robustness_score=_d(pol["minimum_robustness_score"]),
    )

    paths = tuple(
        SimulationPath(
            simulation_id=item["simulation_id"],
            terminal_return_pct=_d(item["terminal_return_pct"]),
            max_drawdown_pct=_d(item["max_drawdown_pct"]),
            ruined=bool(item["ruined"]),
            path_hash=item["path_hash"],
        )
        for item in payload["paths"]
    )

    m = payload["metrics"]
    metrics = MonteCarloMetrics(
        simulation_count=int(m["simulation_count"]),
        mean_terminal_return_pct=_d(m["mean_terminal_return_pct"]),
        median_terminal_return_pct=_d(m["median_terminal_return_pct"]),
        percentile_5_return_pct=_d(m["percentile_5_return_pct"]),
        percentile_25_return_pct=_d(m["percentile_25_return_pct"]),
        percentile_75_return_pct=_d(m["percentile_75_return_pct"]),
        percentile_95_return_pct=_d(m["percentile_95_return_pct"]),
        worst_terminal_return_pct=_d(m["worst_terminal_return_pct"]),
        best_terminal_return_pct=_d(m["best_terminal_return_pct"]),
        mean_max_drawdown_pct=_d(m["mean_max_drawdown_pct"]),
        worst_max_drawdown_pct=_d(m["worst_max_drawdown_pct"]),
        loss_probability=_d(m["loss_probability"]),
        ruin_probability=_d(m["ruin_probability"]),
        value_at_risk_pct=_d(m["value_at_risk_pct"]),
        conditional_value_at_risk_pct=_d(m["conditional_value_at_risk_pct"]),
        robustness_score=_d(m["robustness_score"]),
        validation_passed=bool(m["validation_passed"]),
    )

    result = MonteCarloResult(
        version=payload["version"],
        analysis_id=payload["analysis_id"],
        policy=policy,
        source_return_count=int(payload["source_return_count"]),
        paths=paths,
        metrics=metrics,
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
