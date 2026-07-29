from __future__ import annotations

"""
V29.4 Stress Testing Engine

Features:
- deterministic scenario-based stress testing
- flash crash
- prolonged bear market
- volatility spike
- sideways market
- consecutive-loss streak
- liquidity shock / slippage expansion
- commission shock
- custom scenarios
- terminal return, max drawdown, recovery, survival
- scenario severity and resilience score
- aggregate stress score and validation decision
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
from typing import Any, Iterable, Sequence
import json

VERSION = "29.4"
ZERO = Decimal("0")
ONE = Decimal("1")
Q = Decimal("0.000001")


class StressTestError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise StressTestError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise StressTestError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _mean(values: Sequence[Decimal]) -> Decimal:
    return ZERO if not values else sum(values, ZERO) / Decimal(len(values))


@dataclass(frozen=True)
class StressPolicy:
    survival_equity_floor_pct: Decimal = Decimal("50")
    maximum_acceptable_drawdown_pct: Decimal = Decimal("-40")
    minimum_stress_score: Decimal = Decimal("60")
    recovery_horizon: int = 20

    def __post_init__(self) -> None:
        floor = _d(self.survival_equity_floor_pct)
        if floor <= ZERO or floor >= Decimal("100"):
            raise StressTestError("survival_equity_floor_pct must be between 0 and 100")
        drawdown = _d(self.maximum_acceptable_drawdown_pct)
        if drawdown >= ZERO or drawdown < Decimal("-100"):
            raise StressTestError("maximum_acceptable_drawdown_pct must be negative")
        score = _d(self.minimum_stress_score)
        if score < ZERO or score > Decimal("100"):
            raise StressTestError("minimum_stress_score must be between 0 and 100")
        if self.recovery_horizon < 1:
            raise StressTestError("recovery_horizon must be positive")


@dataclass(frozen=True)
class StressScenario:
    name: str
    return_multiplier: Decimal = Decimal("1")
    additive_return: Decimal = Decimal("0")
    shock_index: int = -1
    shock_return: Decimal = Decimal("0")
    consecutive_loss_count: int = 0
    consecutive_loss_return: Decimal = Decimal("0")
    cost_drag_per_period: Decimal = Decimal("0")
    severity_weight: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise StressTestError("scenario name is required")
        if _d(self.return_multiplier) < ZERO:
            raise StressTestError("return_multiplier cannot be negative")
        if self.shock_index < -1:
            raise StressTestError("shock_index cannot be less than -1")
        if self.consecutive_loss_count < 0:
            raise StressTestError("consecutive_loss_count cannot be negative")
        if _d(self.shock_return) <= Decimal("-1"):
            raise StressTestError("shock_return cannot be <= -100%")
        if _d(self.consecutive_loss_return) <= Decimal("-1"):
            raise StressTestError("consecutive_loss_return cannot be <= -100%")
        if _d(self.severity_weight) <= ZERO:
            raise StressTestError("severity_weight must be positive")


@dataclass(frozen=True)
class ScenarioResult:
    scenario_name: str
    terminal_return_pct: Decimal
    max_drawdown_pct: Decimal
    minimum_equity_pct: Decimal
    recovery_periods: int
    survived: bool
    resilience_score: Decimal
    scenario_hash: str


@dataclass(frozen=True)
class StressMetrics:
    scenario_count: int
    survived_scenarios: int
    survival_ratio: Decimal
    average_terminal_return_pct: Decimal
    worst_terminal_return_pct: Decimal
    average_max_drawdown_pct: Decimal
    worst_max_drawdown_pct: Decimal
    average_resilience_score: Decimal
    stress_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class StressTestResult:
    version: str
    analysis_id: str
    policy: StressPolicy
    scenarios: tuple[StressScenario, ...]
    scenario_results: tuple[ScenarioResult, ...]
    metrics: StressMetrics
    input_hash: str
    result_hash: str


def default_scenarios() -> tuple[StressScenario, ...]:
    return (
        StressScenario(
            name="FLASH_CRASH",
            shock_index=10,
            shock_return=Decimal("-0.22"),
            severity_weight=Decimal("1.4"),
        ),
        StressScenario(
            name="PROLONGED_BEAR_MARKET",
            return_multiplier=Decimal("0.60"),
            additive_return=Decimal("-0.003"),
            severity_weight=Decimal("1.3"),
        ),
        StressScenario(
            name="VOLATILITY_SPIKE",
            return_multiplier=Decimal("1.80"),
            additive_return=Decimal("-0.001"),
            severity_weight=Decimal("1.2"),
        ),
        StressScenario(
            name="SIDEWAYS_MARKET",
            return_multiplier=Decimal("0.15"),
            cost_drag_per_period=Decimal("-0.0005"),
            severity_weight=Decimal("0.8"),
        ),
        StressScenario(
            name="CONSECUTIVE_LOSSES",
            consecutive_loss_count=8,
            consecutive_loss_return=Decimal("-0.025"),
            severity_weight=Decimal("1.2"),
        ),
        StressScenario(
            name="LIQUIDITY_SHOCK",
            cost_drag_per_period=Decimal("-0.003"),
            shock_index=20,
            shock_return=Decimal("-0.08"),
            severity_weight=Decimal("1.1"),
        ),
        StressScenario(
            name="COMMISSION_SHOCK",
            cost_drag_per_period=Decimal("-0.0015"),
            severity_weight=Decimal("0.7"),
        ),
    )


def _policy_payload(policy: StressPolicy) -> dict[str, Any]:
    return {
        "survival_equity_floor_pct": str(policy.survival_equity_floor_pct),
        "maximum_acceptable_drawdown_pct": str(policy.maximum_acceptable_drawdown_pct),
        "minimum_stress_score": str(policy.minimum_stress_score),
        "recovery_horizon": policy.recovery_horizon,
    }


def _scenario_payload(scenario: StressScenario) -> dict[str, Any]:
    return {
        "name": scenario.name,
        "return_multiplier": str(scenario.return_multiplier),
        "additive_return": str(scenario.additive_return),
        "shock_index": scenario.shock_index,
        "shock_return": str(scenario.shock_return),
        "consecutive_loss_count": scenario.consecutive_loss_count,
        "consecutive_loss_return": str(scenario.consecutive_loss_return),
        "cost_drag_per_period": str(scenario.cost_drag_per_period),
        "severity_weight": str(scenario.severity_weight),
    }


def _scenario_result_payload(item: ScenarioResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "scenario_name": item.scenario_name,
        "terminal_return_pct": str(item.terminal_return_pct),
        "max_drawdown_pct": str(item.max_drawdown_pct),
        "minimum_equity_pct": str(item.minimum_equity_pct),
        "recovery_periods": item.recovery_periods,
        "survived": item.survived,
        "resilience_score": str(item.resilience_score),
    }
    if include_hash:
        payload["scenario_hash"] = item.scenario_hash
    return payload


def _metrics_payload(metrics: StressMetrics) -> dict[str, Any]:
    return {
        "scenario_count": metrics.scenario_count,
        "survived_scenarios": metrics.survived_scenarios,
        "survival_ratio": str(metrics.survival_ratio),
        "average_terminal_return_pct": str(metrics.average_terminal_return_pct),
        "worst_terminal_return_pct": str(metrics.worst_terminal_return_pct),
        "average_max_drawdown_pct": str(metrics.average_max_drawdown_pct),
        "worst_max_drawdown_pct": str(metrics.worst_max_drawdown_pct),
        "average_resilience_score": str(metrics.average_resilience_score),
        "stress_score": str(metrics.stress_score),
        "validation_passed": metrics.validation_passed,
    }


def _result_payload(result: StressTestResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "analysis_id": result.analysis_id,
        "policy": _policy_payload(result.policy),
        "scenarios": [_scenario_payload(x) for x in result.scenarios],
        "scenario_results": [_scenario_result_payload(x, include_hash=True) for x in result.scenario_results],
        "metrics": _metrics_payload(result.metrics),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["result_hash"] = result.result_hash
    return payload


def _apply_scenario(base_returns: Sequence[Decimal], scenario: StressScenario) -> tuple[Decimal, ...]:
    stressed = [
        _q(value * _d(scenario.return_multiplier) + _d(scenario.additive_return) + _d(scenario.cost_drag_per_period))
        for value in base_returns
    ]

    if scenario.shock_index >= 0:
        if scenario.shock_index >= len(stressed):
            raise StressTestError("shock_index is outside the return series")
        stressed[scenario.shock_index] = _q(stressed[scenario.shock_index] + _d(scenario.shock_return))

    if scenario.consecutive_loss_count:
        if scenario.consecutive_loss_count > len(stressed):
            raise StressTestError("consecutive_loss_count exceeds return series")
        start = max(0, len(stressed) // 2 - scenario.consecutive_loss_count // 2)
        for index in range(start, start + scenario.consecutive_loss_count):
            stressed[index] = _q(_d(scenario.consecutive_loss_return) + _d(scenario.cost_drag_per_period))

    if any(value <= Decimal("-1") for value in stressed):
        raise StressTestError("stressed return cannot be <= -100%")
    return tuple(stressed)


def _evaluate_path(
    stressed_returns: Sequence[Decimal],
    scenario: StressScenario,
    policy: StressPolicy,
) -> ScenarioResult:
    equity = ONE
    peak = ONE
    minimum_equity = ONE
    max_drawdown = ZERO
    deepest_drawdown_index = 0

    for index, value in enumerate(stressed_returns):
        equity *= ONE + value
        if equity > peak:
            peak = equity
        if equity < minimum_equity:
            minimum_equity = equity
        drawdown = equity / peak - ONE
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            deepest_drawdown_index = index

    recovery_periods = policy.recovery_horizon + 1
    if max_drawdown == ZERO:
        recovery_periods = 0
    else:
        peak_before = ONE
        running = ONE
        for index, value in enumerate(stressed_returns):
            running *= ONE + value
            if index <= deepest_drawdown_index:
                peak_before = max(peak_before, running)
            elif running >= peak_before:
                recovery_periods = index - deepest_drawdown_index
                break

    terminal_return_pct = (equity - ONE) * Decimal("100")
    max_drawdown_pct = max_drawdown * Decimal("100")
    minimum_equity_pct = minimum_equity * Decimal("100")

    survived = (
        minimum_equity_pct >= _d(policy.survival_equity_floor_pct)
        and max_drawdown_pct >= _d(policy.maximum_acceptable_drawdown_pct)
    )

    return_component = max(ZERO, min(Decimal("50"), Decimal("50") + terminal_return_pct))
    drawdown_component = max(ZERO, Decimal("30") - abs(max_drawdown_pct) * Decimal("0.75"))
    recovery_component = max(
        ZERO,
        Decimal("20")
        * (ONE - min(ONE, Decimal(recovery_periods) / Decimal(policy.recovery_horizon)))
    )
    raw_score = return_component + drawdown_component + recovery_component
    resilience = max(
        ZERO,
        min(Decimal("100"), raw_score / _d(scenario.severity_weight))
    )

    result = ScenarioResult(
        scenario_name=scenario.name,
        terminal_return_pct=_q(terminal_return_pct),
        max_drawdown_pct=_q(max_drawdown_pct),
        minimum_equity_pct=_q(minimum_equity_pct),
        recovery_periods=recovery_periods,
        survived=survived,
        resilience_score=_q(resilience),
        scenario_hash="",
    )
    return replace(result, scenario_hash=_hash(_scenario_result_payload(result)))


def run_stress_test(
    returns: Iterable[Any],
    scenarios: Iterable[StressScenario] | None = None,
    policy: StressPolicy | None = None,
) -> StressTestResult:
    selected_policy = policy or StressPolicy()
    normalized_returns = tuple(_q(value) for value in returns)
    selected_scenarios = tuple(scenarios) if scenarios is not None else default_scenarios()

    if len(normalized_returns) < 20:
        raise StressTestError("at least twenty returns are required")
    if any(value <= Decimal("-1") for value in normalized_returns):
        raise StressTestError("return cannot be <= -100%")
    if not selected_scenarios:
        raise StressTestError("at least one stress scenario is required")
    names = [scenario.name for scenario in selected_scenarios]
    if len(set(names)) != len(names):
        raise StressTestError("duplicate scenario names detected")

    scenario_results = []
    weighted_scores = []
    total_weight = ZERO

    for scenario in selected_scenarios:
        stressed = _apply_scenario(normalized_returns, scenario)
        result = _evaluate_path(stressed, scenario, selected_policy)
        scenario_results.append(result)
        weight = _d(scenario.severity_weight)
        weighted_scores.append(result.resilience_score * weight)
        total_weight += weight

    survived_count = sum(1 for x in scenario_results if x.survived)
    terminal_returns = [x.terminal_return_pct for x in scenario_results]
    drawdowns = [x.max_drawdown_pct for x in scenario_results]
    resilience_scores = [x.resilience_score for x in scenario_results]
    survival_ratio = Decimal(survived_count) / Decimal(len(scenario_results))

    weighted_average = ZERO if total_weight == ZERO else sum(weighted_scores, ZERO) / total_weight
    stress_score = (
        weighted_average * Decimal("0.70")
        + survival_ratio * Decimal("100") * Decimal("0.30")
    )

    metrics = StressMetrics(
        scenario_count=len(scenario_results),
        survived_scenarios=survived_count,
        survival_ratio=_q(survival_ratio),
        average_terminal_return_pct=_q(_mean(terminal_returns)),
        worst_terminal_return_pct=_q(min(terminal_returns)),
        average_max_drawdown_pct=_q(_mean(drawdowns)),
        worst_max_drawdown_pct=_q(min(drawdowns)),
        average_resilience_score=_q(_mean(resilience_scores)),
        stress_score=_q(stress_score),
        validation_passed=(
            stress_score >= _d(selected_policy.minimum_stress_score)
            and survival_ratio >= Decimal("0.70")
        ),
    )

    input_hash = _hash({
        "returns": [str(value) for value in normalized_returns],
        "scenarios": [_scenario_payload(x) for x in selected_scenarios],
        "policy": _policy_payload(selected_policy),
    })

    result = StressTestResult(
        version=VERSION,
        analysis_id=f"STR-{input_hash[:16].upper()}",
        policy=selected_policy,
        scenarios=selected_scenarios,
        scenario_results=tuple(scenario_results),
        metrics=metrics,
        input_hash=input_hash,
        result_hash="",
    )
    return replace(result, result_hash=_hash(_result_payload(result)))


def verify_scenario_result(item: ScenarioResult) -> bool:
    if item.max_drawdown_pct > ZERO:
        raise StressTestError("maximum drawdown cannot be positive")
    if item.minimum_equity_pct <= ZERO:
        raise StressTestError("minimum equity must be positive")
    if item.recovery_periods < 0:
        raise StressTestError("recovery periods cannot be negative")
    if item.resilience_score < ZERO or item.resilience_score > Decimal("100"):
        raise StressTestError("invalid resilience score")
    clean = replace(item, scenario_hash="")
    if item.scenario_hash != _hash(_scenario_result_payload(clean)):
        raise StressTestError("scenario result hash mismatch")
    return True


def verify_result(result: StressTestResult) -> bool:
    if result.version != VERSION:
        raise StressTestError("unsupported version")
    if not result.analysis_id.startswith("STR-"):
        raise StressTestError("invalid analysis ID")
    if result.metrics.scenario_count != len(result.scenario_results):
        raise StressTestError("scenario count mismatch")
    if len(result.scenarios) != len(result.scenario_results):
        raise StressTestError("scenario definition/result mismatch")
    if result.metrics.survival_ratio < ZERO or result.metrics.survival_ratio > ONE:
        raise StressTestError("invalid survival ratio")
    if result.metrics.stress_score < ZERO or result.metrics.stress_score > Decimal("100"):
        raise StressTestError("invalid stress score")
    for item in result.scenario_results:
        verify_scenario_result(item)
    clean = replace(result, result_hash="")
    if result.result_hash != _hash(_result_payload(clean)):
        raise StressTestError("stress-test result hash mismatch")
    return True


def save_result(result: StressTestResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> StressTestResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    pol = payload["policy"]
    policy = StressPolicy(
        survival_equity_floor_pct=_d(pol["survival_equity_floor_pct"]),
        maximum_acceptable_drawdown_pct=_d(pol["maximum_acceptable_drawdown_pct"]),
        minimum_stress_score=_d(pol["minimum_stress_score"]),
        recovery_horizon=int(pol["recovery_horizon"]),
    )

    scenarios = tuple(
        StressScenario(
            name=x["name"],
            return_multiplier=_d(x["return_multiplier"]),
            additive_return=_d(x["additive_return"]),
            shock_index=int(x["shock_index"]),
            shock_return=_d(x["shock_return"]),
            consecutive_loss_count=int(x["consecutive_loss_count"]),
            consecutive_loss_return=_d(x["consecutive_loss_return"]),
            cost_drag_per_period=_d(x["cost_drag_per_period"]),
            severity_weight=_d(x["severity_weight"]),
        )
        for x in payload["scenarios"]
    )

    scenario_results = tuple(
        ScenarioResult(
            scenario_name=x["scenario_name"],
            terminal_return_pct=_d(x["terminal_return_pct"]),
            max_drawdown_pct=_d(x["max_drawdown_pct"]),
            minimum_equity_pct=_d(x["minimum_equity_pct"]),
            recovery_periods=int(x["recovery_periods"]),
            survived=bool(x["survived"]),
            resilience_score=_d(x["resilience_score"]),
            scenario_hash=x["scenario_hash"],
        )
        for x in payload["scenario_results"]
    )

    m = payload["metrics"]
    metrics = StressMetrics(
        scenario_count=int(m["scenario_count"]),
        survived_scenarios=int(m["survived_scenarios"]),
        survival_ratio=_d(m["survival_ratio"]),
        average_terminal_return_pct=_d(m["average_terminal_return_pct"]),
        worst_terminal_return_pct=_d(m["worst_terminal_return_pct"]),
        average_max_drawdown_pct=_d(m["average_max_drawdown_pct"]),
        worst_max_drawdown_pct=_d(m["worst_max_drawdown_pct"]),
        average_resilience_score=_d(m["average_resilience_score"]),
        stress_score=_d(m["stress_score"]),
        validation_passed=bool(m["validation_passed"]),
    )

    result = StressTestResult(
        version=payload["version"],
        analysis_id=payload["analysis_id"],
        policy=policy,
        scenarios=scenarios,
        scenario_results=scenario_results,
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
