from __future__ import annotations

"""
V29.5A Professional Report Engine Core

Features:
- unified report inputs for V29.0 through V29.4 outputs
- executive summary
- performance, risk, walk-forward, Monte Carlo, and stress summaries
- weighted overall score
- letter grade A through F
- recommendation classification
- deterministic JSON-compatible report model
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
from typing import Any
from datetime import datetime, timezone
import json

VERSION = "29.5A"
ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
Q = Decimal("0.000001")


class ReportError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ReportError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ReportError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def _clamp(value: Any, low: Decimal = ZERO, high: Decimal = ONE_HUNDRED) -> Decimal:
    return _q(max(low, min(high, _d(value))))


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReportPolicy:
    performance_weight: Decimal = Decimal("0.30")
    risk_weight: Decimal = Decimal("0.25")
    walk_forward_weight: Decimal = Decimal("0.15")
    monte_carlo_weight: Decimal = Decimal("0.15")
    stress_weight: Decimal = Decimal("0.15")
    minimum_recommended_score: Decimal = Decimal("70")
    minimum_acceptable_score: Decimal = Decimal("55")

    def __post_init__(self) -> None:
        weights = [
            _d(self.performance_weight),
            _d(self.risk_weight),
            _d(self.walk_forward_weight),
            _d(self.monte_carlo_weight),
            _d(self.stress_weight),
        ]
        if any(value < ZERO for value in weights):
            raise ReportError("weights cannot be negative")
        if sum(weights, ZERO) != Decimal("1"):
            raise ReportError("report weights must total 1")
        recommended = _d(self.minimum_recommended_score)
        acceptable = _d(self.minimum_acceptable_score)
        if recommended < ZERO or recommended > ONE_HUNDRED:
            raise ReportError("minimum_recommended_score must be between 0 and 100")
        if acceptable < ZERO or acceptable > ONE_HUNDRED:
            raise ReportError("minimum_acceptable_score must be between 0 and 100")
        if acceptable > recommended:
            raise ReportError("minimum_acceptable_score cannot exceed recommended score")


@dataclass(frozen=True)
class PerformanceInput:
    total_return_pct: Decimal
    cagr_pct: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    profit_factor: Decimal
    win_rate: Decimal
    alpha_pct: Decimal
    information_ratio: Decimal


@dataclass(frozen=True)
class RiskInput:
    max_drawdown_pct: Decimal
    annualized_volatility_pct: Decimal
    value_at_risk_pct: Decimal
    conditional_value_at_risk_pct: Decimal
    exposure_ratio: Decimal
    ruin_probability: Decimal


@dataclass(frozen=True)
class WalkForwardInput:
    total_windows: int
    profitable_window_ratio: Decimal
    average_out_of_sample_return_pct: Decimal
    parameter_stability_ratio: Decimal
    overfitting_risk_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class MonteCarloInput:
    simulation_count: int
    mean_terminal_return_pct: Decimal
    percentile_5_return_pct: Decimal
    loss_probability: Decimal
    ruin_probability: Decimal
    robustness_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class StressInput:
    scenario_count: int
    survival_ratio: Decimal
    worst_terminal_return_pct: Decimal
    worst_max_drawdown_pct: Decimal
    average_resilience_score: Decimal
    stress_score: Decimal
    validation_passed: bool


@dataclass(frozen=True)
class ComponentScore:
    name: str
    score: Decimal
    status: str
    explanation: str


@dataclass(frozen=True)
class ExecutiveSummary:
    strategy_name: str
    report_timestamp: str
    overall_score: Decimal
    overall_grade: str
    recommendation: str
    validation_passed: bool
    summary_text: str


@dataclass(frozen=True)
class ProfessionalReport:
    version: str
    report_id: str
    policy: ReportPolicy
    executive_summary: ExecutiveSummary
    component_scores: tuple[ComponentScore, ...]
    performance: PerformanceInput
    risk: RiskInput
    walk_forward: WalkForwardInput
    monte_carlo: MonteCarloInput
    stress: StressInput
    source_hashes: tuple[tuple[str, str], ...]
    report_hash: str


def _policy_payload(policy: ReportPolicy) -> dict[str, Any]:
    return {
        "performance_weight": str(policy.performance_weight),
        "risk_weight": str(policy.risk_weight),
        "walk_forward_weight": str(policy.walk_forward_weight),
        "monte_carlo_weight": str(policy.monte_carlo_weight),
        "stress_weight": str(policy.stress_weight),
        "minimum_recommended_score": str(policy.minimum_recommended_score),
        "minimum_acceptable_score": str(policy.minimum_acceptable_score),
    }


def _dataclass_decimal_payload(value: Any) -> dict[str, Any]:
    output = {}
    for name in value.__dataclass_fields__:
        item = getattr(value, name)
        if isinstance(item, Decimal):
            output[name] = str(item)
        else:
            output[name] = item
    return output


def _component_payload(item: ComponentScore) -> dict[str, Any]:
    return {
        "name": item.name,
        "score": str(item.score),
        "status": item.status,
        "explanation": item.explanation,
    }


def _executive_payload(item: ExecutiveSummary) -> dict[str, Any]:
    return {
        "strategy_name": item.strategy_name,
        "report_timestamp": item.report_timestamp,
        "overall_score": str(item.overall_score),
        "overall_grade": item.overall_grade,
        "recommendation": item.recommendation,
        "validation_passed": item.validation_passed,
        "summary_text": item.summary_text,
    }


def _report_payload(report: ProfessionalReport, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": report.version,
        "report_id": report.report_id,
        "policy": _policy_payload(report.policy),
        "executive_summary": _executive_payload(report.executive_summary),
        "component_scores": [_component_payload(x) for x in report.component_scores],
        "performance": _dataclass_decimal_payload(report.performance),
        "risk": _dataclass_decimal_payload(report.risk),
        "walk_forward": _dataclass_decimal_payload(report.walk_forward),
        "monte_carlo": _dataclass_decimal_payload(report.monte_carlo),
        "stress": _dataclass_decimal_payload(report.stress),
        "source_hashes": [[k, v] for k, v in report.source_hashes],
    }
    if include_hash:
        payload["report_hash"] = report.report_hash
    return payload


def _status(score: Decimal) -> str:
    if score >= Decimal("85"):
        return "EXCELLENT"
    if score >= Decimal("70"):
        return "GOOD"
    if score >= Decimal("55"):
        return "ACCEPTABLE"
    if score >= Decimal("40"):
        return "WEAK"
    return "POOR"


def _grade(score: Decimal) -> str:
    if score >= Decimal("90"):
        return "A"
    if score >= Decimal("80"):
        return "B"
    if score >= Decimal("70"):
        return "C"
    if score >= Decimal("60"):
        return "D"
    return "F"


def _performance_score(value: PerformanceInput) -> Decimal:
    score = Decimal("50")
    score += min(Decimal("20"), max(Decimal("-20"), _d(value.cagr_pct)))
    score += min(Decimal("10"), max(Decimal("-10"), _d(value.sharpe_ratio) * Decimal("5")))
    score += min(Decimal("7"), max(Decimal("-7"), _d(value.sortino_ratio) * Decimal("2.5")))
    score += min(Decimal("5"), max(Decimal("-5"), _d(value.calmar_ratio) * Decimal("2")))
    score += min(Decimal("5"), max(Decimal("-5"), (_d(value.profit_factor) - Decimal("1")) * Decimal("5")))
    score += min(Decimal("3"), max(Decimal("-3"), _d(value.alpha_pct) / Decimal("3")))
    return _clamp(score)


def _risk_score(value: RiskInput) -> Decimal:
    drawdown_penalty = min(Decimal("45"), abs(_d(value.max_drawdown_pct)) * Decimal("1.2"))
    volatility_penalty = min(Decimal("20"), max(ZERO, _d(value.annualized_volatility_pct) - Decimal("10")) * Decimal("0.8"))
    var_penalty = min(Decimal("10"), abs(min(ZERO, _d(value.value_at_risk_pct))) * Decimal("0.5"))
    cvar_penalty = min(Decimal("10"), abs(min(ZERO, _d(value.conditional_value_at_risk_pct))) * Decimal("0.3"))
    ruin_penalty = min(Decimal("15"), _d(value.ruin_probability) * Decimal("100"))
    return _clamp(ONE_HUNDRED - drawdown_penalty - volatility_penalty - var_penalty - cvar_penalty - ruin_penalty)


def _walk_forward_score(value: WalkForwardInput) -> Decimal:
    score = (
        _d(value.profitable_window_ratio) * Decimal("35")
        + _d(value.parameter_stability_ratio) * Decimal("25")
        + max(ZERO, Decimal("20") - _d(value.overfitting_risk_score) * Decimal("0.2"))
        + min(Decimal("15"), max(ZERO, _d(value.average_out_of_sample_return_pct)))
        + (Decimal("5") if value.validation_passed else ZERO)
    )
    return _clamp(score)


def _monte_carlo_score(value: MonteCarloInput) -> Decimal:
    score = (
        _d(value.robustness_score) * Decimal("0.65")
        + (ONE_HUNDRED - _d(value.loss_probability) * ONE_HUNDRED) * Decimal("0.15")
        + (ONE_HUNDRED - _d(value.ruin_probability) * ONE_HUNDRED) * Decimal("0.15")
        + (Decimal("5") if value.validation_passed else ZERO)
    )
    return _clamp(score)


def _stress_score(value: StressInput) -> Decimal:
    score = (
        _d(value.stress_score) * Decimal("0.50")
        + _d(value.average_resilience_score) * Decimal("0.25")
        + _d(value.survival_ratio) * ONE_HUNDRED * Decimal("0.20")
        + (Decimal("5") if value.validation_passed else ZERO)
    )
    return _clamp(score)


def _validate_inputs(
    strategy_name: str,
    performance: PerformanceInput,
    risk: RiskInput,
    walk_forward: WalkForwardInput,
    monte_carlo: MonteCarloInput,
    stress: StressInput,
    source_hashes: tuple[tuple[str, str], ...],
) -> None:
    if not strategy_name.strip():
        raise ReportError("strategy_name is required")
    if not ZERO <= _d(performance.win_rate) <= Decimal("1"):
        raise ReportError("win_rate must be between 0 and 1")
    if risk.max_drawdown_pct > ZERO:
        raise ReportError("max_drawdown_pct cannot be positive")
    if not ZERO <= _d(risk.exposure_ratio):
        raise ReportError("exposure_ratio cannot be negative")
    for name, value in (
        ("risk.ruin_probability", risk.ruin_probability),
        ("walk_forward.profitable_window_ratio", walk_forward.profitable_window_ratio),
        ("walk_forward.parameter_stability_ratio", walk_forward.parameter_stability_ratio),
        ("monte_carlo.loss_probability", monte_carlo.loss_probability),
        ("monte_carlo.ruin_probability", monte_carlo.ruin_probability),
        ("stress.survival_ratio", stress.survival_ratio),
    ):
        if not ZERO <= _d(value) <= Decimal("1"):
            raise ReportError(f"{name} must be between 0 and 1")
    if walk_forward.total_windows < 1:
        raise ReportError("walk-forward windows must be positive")
    if monte_carlo.simulation_count < 100:
        raise ReportError("Monte Carlo simulation_count must be at least 100")
    if stress.scenario_count < 1:
        raise ReportError("stress scenario_count must be positive")
    if len(source_hashes) < 5:
        raise ReportError("five source hashes are required")
    keys = [key for key, _ in source_hashes]
    if len(set(keys)) != len(keys):
        raise ReportError("source hash names must be unique")
    for key, digest in source_hashes:
        if not key.strip():
            raise ReportError("source hash name is required")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest.lower()):
            raise ReportError("source hashes must be SHA-256 hex digests")


def create_professional_report(
    strategy_name: str,
    performance: PerformanceInput,
    risk: RiskInput,
    walk_forward: WalkForwardInput,
    monte_carlo: MonteCarloInput,
    stress: StressInput,
    source_hashes: tuple[tuple[str, str], ...],
    policy: ReportPolicy | None = None,
    report_timestamp: str | None = None,
) -> ProfessionalReport:
    selected = policy or ReportPolicy()
    normalized_hashes = tuple(sorted((str(k), str(v).lower()) for k, v in source_hashes))
    _validate_inputs(
        strategy_name,
        performance,
        risk,
        walk_forward,
        monte_carlo,
        stress,
        normalized_hashes,
    )

    scores = (
        ComponentScore(
            "PERFORMANCE",
            _performance_score(performance),
            "",
            "Return quality, risk-adjusted performance, and trading efficiency.",
        ),
        ComponentScore(
            "RISK",
            _risk_score(risk),
            "",
            "Drawdown, volatility, tail risk, exposure, and ruin probability.",
        ),
        ComponentScore(
            "WALK_FORWARD",
            _walk_forward_score(walk_forward),
            "",
            "Out-of-sample profitability, parameter stability, and overfitting control.",
        ),
        ComponentScore(
            "MONTE_CARLO",
            _monte_carlo_score(monte_carlo),
            "",
            "Return-path robustness, loss probability, and ruin probability.",
        ),
        ComponentScore(
            "STRESS",
            _stress_score(stress),
            "",
            "Survival and resilience under severe market and cost shocks.",
        ),
    )
    scores = tuple(replace(item, status=_status(item.score)) for item in scores)

    score_map = {item.name: item.score for item in scores}
    overall = _q(
        score_map["PERFORMANCE"] * _d(selected.performance_weight)
        + score_map["RISK"] * _d(selected.risk_weight)
        + score_map["WALK_FORWARD"] * _d(selected.walk_forward_weight)
        + score_map["MONTE_CARLO"] * _d(selected.monte_carlo_weight)
        + score_map["STRESS"] * _d(selected.stress_weight)
    )

    passed = (
        walk_forward.validation_passed
        and monte_carlo.validation_passed
        and stress.validation_passed
        and overall >= _d(selected.minimum_acceptable_score)
    )

    if overall >= _d(selected.minimum_recommended_score) and passed:
        recommendation = "RECOMMENDED_FOR_PAPER_TRADING"
    elif overall >= _d(selected.minimum_acceptable_score):
        recommendation = "CONDITIONALLY_ACCEPTABLE"
    else:
        recommendation = "NOT_RECOMMENDED"

    timestamp = report_timestamp or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception as exc:
        raise ReportError("report_timestamp must be ISO-8601 compatible") from exc

    grade = _grade(overall)
    summary_text = (
        f"{strategy_name} received grade {grade} with an overall score of {overall}. "
        f"Final recommendation: {recommendation}."
    )

    executive = ExecutiveSummary(
        strategy_name=strategy_name.strip(),
        report_timestamp=timestamp,
        overall_score=overall,
        overall_grade=grade,
        recommendation=recommendation,
        validation_passed=passed,
        summary_text=summary_text,
    )

    report_seed = {
        "strategy_name": executive.strategy_name,
        "report_timestamp": timestamp,
        "source_hashes": [[k, v] for k, v in normalized_hashes],
        "scores": [_component_payload(x) for x in scores],
    }

    report = ProfessionalReport(
        version=VERSION,
        report_id=f"RPT-{_hash(report_seed)[:16].upper()}",
        policy=selected,
        executive_summary=executive,
        component_scores=scores,
        performance=performance,
        risk=risk,
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
        stress=stress,
        source_hashes=normalized_hashes,
        report_hash="",
    )
    return replace(report, report_hash=_hash(_report_payload(report)))


def verify_report(report: ProfessionalReport) -> bool:
    if report.version != VERSION:
        raise ReportError("unsupported report version")
    if not report.report_id.startswith("RPT-"):
        raise ReportError("invalid report ID")
    if len(report.component_scores) != 5:
        raise ReportError("exactly five component scores are required")
    names = [item.name for item in report.component_scores]
    if set(names) != {"PERFORMANCE", "RISK", "WALK_FORWARD", "MONTE_CARLO", "STRESS"}:
        raise ReportError("invalid component score set")
    for item in report.component_scores:
        if item.score < ZERO or item.score > ONE_HUNDRED:
            raise ReportError("component score outside valid range")
        if item.status != _status(item.score):
            raise ReportError("component status mismatch")
    if report.executive_summary.overall_grade != _grade(report.executive_summary.overall_score):
        raise ReportError("overall grade mismatch")
    if report.executive_summary.overall_score < ZERO or report.executive_summary.overall_score > ONE_HUNDRED:
        raise ReportError("overall score outside valid range")
    clean = replace(report, report_hash="")
    if report.report_hash != _hash(_report_payload(clean)):
        raise ReportError("report hash mismatch")
    return True


def save_report(report: ProfessionalReport, path: str | Path) -> Path:
    verify_report(report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_report_payload(report, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_report(path: str | Path) -> ProfessionalReport:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    p = payload["policy"]
    policy = ReportPolicy(
        performance_weight=_d(p["performance_weight"]),
        risk_weight=_d(p["risk_weight"]),
        walk_forward_weight=_d(p["walk_forward_weight"]),
        monte_carlo_weight=_d(p["monte_carlo_weight"]),
        stress_weight=_d(p["stress_weight"]),
        minimum_recommended_score=_d(p["minimum_recommended_score"]),
        minimum_acceptable_score=_d(p["minimum_acceptable_score"]),
    )

    e = payload["executive_summary"]
    executive = ExecutiveSummary(
        strategy_name=e["strategy_name"],
        report_timestamp=e["report_timestamp"],
        overall_score=_d(e["overall_score"]),
        overall_grade=e["overall_grade"],
        recommendation=e["recommendation"],
        validation_passed=bool(e["validation_passed"]),
        summary_text=e["summary_text"],
    )

    components = tuple(
        ComponentScore(
            name=x["name"],
            score=_d(x["score"]),
            status=x["status"],
            explanation=x["explanation"],
        )
        for x in payload["component_scores"]
    )

    performance = PerformanceInput(**{
        k: _d(v) for k, v in payload["performance"].items()
    })
    risk = RiskInput(**{
        k: _d(v) for k, v in payload["risk"].items()
    })

    wf = payload["walk_forward"]
    walk_forward = WalkForwardInput(
        total_windows=int(wf["total_windows"]),
        profitable_window_ratio=_d(wf["profitable_window_ratio"]),
        average_out_of_sample_return_pct=_d(wf["average_out_of_sample_return_pct"]),
        parameter_stability_ratio=_d(wf["parameter_stability_ratio"]),
        overfitting_risk_score=_d(wf["overfitting_risk_score"]),
        validation_passed=bool(wf["validation_passed"]),
    )

    mc = payload["monte_carlo"]
    monte_carlo = MonteCarloInput(
        simulation_count=int(mc["simulation_count"]),
        mean_terminal_return_pct=_d(mc["mean_terminal_return_pct"]),
        percentile_5_return_pct=_d(mc["percentile_5_return_pct"]),
        loss_probability=_d(mc["loss_probability"]),
        ruin_probability=_d(mc["ruin_probability"]),
        robustness_score=_d(mc["robustness_score"]),
        validation_passed=bool(mc["validation_passed"]),
    )

    st = payload["stress"]
    stress = StressInput(
        scenario_count=int(st["scenario_count"]),
        survival_ratio=_d(st["survival_ratio"]),
        worst_terminal_return_pct=_d(st["worst_terminal_return_pct"]),
        worst_max_drawdown_pct=_d(st["worst_max_drawdown_pct"]),
        average_resilience_score=_d(st["average_resilience_score"]),
        stress_score=_d(st["stress_score"]),
        validation_passed=bool(st["validation_passed"]),
    )

    report = ProfessionalReport(
        version=payload["version"],
        report_id=payload["report_id"],
        policy=policy,
        executive_summary=executive,
        component_scores=components,
        performance=performance,
        risk=risk,
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
        stress=stress,
        source_hashes=tuple((str(k), str(v)) for k, v in payload["source_hashes"]),
        report_hash=payload["report_hash"],
    )
    verify_report(report)
    return report


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
