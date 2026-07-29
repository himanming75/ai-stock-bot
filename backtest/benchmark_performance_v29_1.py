from __future__ import annotations

"""
V29.1 Benchmark & Advanced Performance Analysis

Features:
- strategy versus benchmark comparison
- total return and CAGR
- annualized volatility
- Sharpe and Sortino ratios
- maximum drawdown and drawdown duration
- Calmar and MAR ratios
- alpha and beta
- benchmark correlation
- tracking error and information ratio
- upside/downside capture
- monthly and yearly returns
- rolling return and rolling Sharpe snapshots
- deterministic SHA-256 integrity verification
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
from typing import Any, Iterable
from datetime import datetime
import json

VERSION = "29.1"
ZERO = Decimal("0")
ONE = Decimal("1")
Q = Decimal("0.000001")


class PerformanceError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise PerformanceError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise PerformanceError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(Q, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PerformancePolicy:
    annualization_factor: int = 252
    risk_free_rate_pct: Decimal = Decimal("0")
    rolling_window: int = 20

    def __post_init__(self) -> None:
        if self.annualization_factor <= 0:
            raise PerformanceError("annualization_factor must be positive")
        if self.rolling_window < 2:
            raise PerformanceError("rolling_window must be at least 2")
        _d(self.risk_free_rate_pct)


@dataclass(frozen=True)
class EquityObservation:
    timestamp: str
    strategy_equity: Decimal
    benchmark_equity: Decimal


@dataclass(frozen=True)
class PeriodReturn:
    period: str
    strategy_return_pct: Decimal
    benchmark_return_pct: Decimal
    excess_return_pct: Decimal


@dataclass(frozen=True)
class RollingSnapshot:
    timestamp: str
    strategy_return_pct: Decimal
    benchmark_return_pct: Decimal
    rolling_sharpe: Decimal


@dataclass(frozen=True)
class AdvancedMetrics:
    strategy_total_return_pct: Decimal
    benchmark_total_return_pct: Decimal
    excess_total_return_pct: Decimal
    strategy_cagr_pct: Decimal
    benchmark_cagr_pct: Decimal
    annualized_volatility_pct: Decimal
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    max_drawdown_pct: Decimal
    max_drawdown_duration: int
    calmar_ratio: Decimal
    mar_ratio: Decimal
    alpha_pct: Decimal
    beta: Decimal
    correlation: Decimal
    tracking_error_pct: Decimal
    information_ratio: Decimal
    upside_capture_pct: Decimal
    downside_capture_pct: Decimal


@dataclass(frozen=True)
class PerformanceReport:
    version: str
    report_id: str
    policy: PerformancePolicy
    observations: tuple[EquityObservation, ...]
    metrics: AdvancedMetrics
    monthly_returns: tuple[PeriodReturn, ...]
    yearly_returns: tuple[PeriodReturn, ...]
    rolling_snapshots: tuple[RollingSnapshot, ...]
    input_hash: str
    report_hash: str


def _policy_payload(policy: PerformancePolicy) -> dict[str, Any]:
    return {
        "annualization_factor": policy.annualization_factor,
        "risk_free_rate_pct": str(policy.risk_free_rate_pct),
        "rolling_window": policy.rolling_window,
    }


def _observation_payload(item: EquityObservation) -> dict[str, Any]:
    return {
        "timestamp": item.timestamp,
        "strategy_equity": str(item.strategy_equity),
        "benchmark_equity": str(item.benchmark_equity),
    }


def _period_payload(item: PeriodReturn) -> dict[str, Any]:
    return {
        "period": item.period,
        "strategy_return_pct": str(item.strategy_return_pct),
        "benchmark_return_pct": str(item.benchmark_return_pct),
        "excess_return_pct": str(item.excess_return_pct),
    }


def _rolling_payload(item: RollingSnapshot) -> dict[str, Any]:
    return {
        "timestamp": item.timestamp,
        "strategy_return_pct": str(item.strategy_return_pct),
        "benchmark_return_pct": str(item.benchmark_return_pct),
        "rolling_sharpe": str(item.rolling_sharpe),
    }


def _metrics_payload(item: AdvancedMetrics) -> dict[str, Any]:
    return {name: str(getattr(item, name)) if name != "max_drawdown_duration"
            else item.max_drawdown_duration
            for name in item.__dataclass_fields__}


def _report_payload(report: PerformanceReport, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": report.version,
        "report_id": report.report_id,
        "policy": _policy_payload(report.policy),
        "observations": [_observation_payload(x) for x in report.observations],
        "metrics": _metrics_payload(report.metrics),
        "monthly_returns": [_period_payload(x) for x in report.monthly_returns],
        "yearly_returns": [_period_payload(x) for x in report.yearly_returns],
        "rolling_snapshots": [_rolling_payload(x) for x in report.rolling_snapshots],
        "input_hash": report.input_hash,
    }
    if include_hash:
        payload["report_hash"] = report.report_hash
    return payload


def _returns(values: list[Decimal]) -> list[Decimal]:
    output = []
    for previous, current in zip(values, values[1:]):
        if previous <= ZERO:
            raise PerformanceError("equity values must remain positive")
        output.append(current / previous - ONE)
    return output


def _mean(values: list[Decimal]) -> Decimal:
    return ZERO if not values else sum(values, ZERO) / Decimal(len(values))


def _variance(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    avg = _mean(values)
    return sum((x - avg) ** 2 for x in values) / Decimal(len(values))


def _std(values: list[Decimal]) -> Decimal:
    return _d(sqrt(float(_variance(values))))


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == ZERO:
        return ZERO
    return numerator / denominator


def _annualized_return(total_ratio: Decimal, periods: int, factor: int) -> Decimal:
    if total_ratio <= ZERO or periods <= 0:
        return ZERO
    years = Decimal(periods) / Decimal(factor)
    return _d(float(total_ratio) ** (1.0 / float(years)) - 1.0)


def _drawdown(values: list[Decimal]) -> tuple[Decimal, int]:
    peak = values[0]
    max_dd = ZERO
    duration = 0
    max_duration = 0
    for value in values:
        if value >= peak:
            peak = value
            duration = 0
        else:
            duration += 1
            max_duration = max(max_duration, duration)
            max_dd = min(max_dd, value / peak - ONE)
    return max_dd, max_duration


def _group_periods(
    observations: tuple[EquityObservation, ...],
    fmt: str,
) -> tuple[PeriodReturn, ...]:
    grouped: dict[str, list[EquityObservation]] = {}
    for item in observations:
        key = datetime.fromisoformat(item.timestamp).strftime(fmt)
        grouped.setdefault(key, []).append(item)

    output = []
    for period in sorted(grouped):
        rows = grouped[period]
        s = rows[-1].strategy_equity / rows[0].strategy_equity - ONE
        b = rows[-1].benchmark_equity / rows[0].benchmark_equity - ONE
        output.append(PeriodReturn(
            period=period,
            strategy_return_pct=_q(s * Decimal("100")),
            benchmark_return_pct=_q(b * Decimal("100")),
            excess_return_pct=_q((s - b) * Decimal("100")),
        ))
    return tuple(output)


def analyze_performance(
    observations: Iterable[EquityObservation],
    policy: PerformancePolicy | None = None,
) -> PerformanceReport:
    selected = policy or PerformancePolicy()
    raw = tuple(observations)
    if len(raw) < 3:
        raise PerformanceError("at least three observations are required")

    normalized = []
    previous_time = None
    for item in raw:
        try:
            parsed = datetime.fromisoformat(item.timestamp)
        except Exception as exc:
            raise PerformanceError("timestamp must be ISO-8601 compatible") from exc
        if previous_time is not None and parsed <= previous_time:
            raise PerformanceError("timestamps must be strictly increasing")
        previous_time = parsed
        strategy = _q(item.strategy_equity)
        benchmark = _q(item.benchmark_equity)
        if strategy <= ZERO or benchmark <= ZERO:
            raise PerformanceError("equity values must be positive")
        normalized.append(EquityObservation(item.timestamp, strategy, benchmark))

    data = tuple(normalized)
    strategy_values = [x.strategy_equity for x in data]
    benchmark_values = [x.benchmark_equity for x in data]
    sr = _returns(strategy_values)
    br = _returns(benchmark_values)
    excess = [s - b for s, b in zip(sr, br)]

    factor = Decimal(selected.annualization_factor)
    rf_daily = (_d(selected.risk_free_rate_pct) / Decimal("100")) / factor
    excess_rf = [x - rf_daily for x in sr]

    strategy_total = strategy_values[-1] / strategy_values[0] - ONE
    benchmark_total = benchmark_values[-1] / benchmark_values[0] - ONE
    strategy_cagr = _annualized_return(strategy_values[-1] / strategy_values[0], len(sr), selected.annualization_factor)
    benchmark_cagr = _annualized_return(benchmark_values[-1] / benchmark_values[0], len(br), selected.annualization_factor)
    volatility = _std(sr) * _d(sqrt(selected.annualization_factor))
    sharpe = _safe_ratio(_mean(excess_rf), _std(excess_rf)) * _d(sqrt(selected.annualization_factor))

    downside = [min(x - rf_daily, ZERO) for x in sr]
    downside_dev = _d(sqrt(float(_mean([x * x for x in downside]))))
    sortino = _safe_ratio(_mean(excess_rf), downside_dev) * _d(sqrt(selected.annualization_factor))

    max_dd, max_duration = _drawdown(strategy_values)
    calmar = _safe_ratio(strategy_cagr, abs(max_dd))
    mar = calmar

    benchmark_variance = _variance(br)
    covariance = ZERO
    if br:
        avg_s = _mean(sr)
        avg_b = _mean(br)
        covariance = sum((s - avg_s) * (b - avg_b) for s, b in zip(sr, br)) / Decimal(len(br))
    beta = _safe_ratio(covariance, benchmark_variance)
    alpha_daily = _mean(sr) - (rf_daily + beta * (_mean(br) - rf_daily))
    alpha = alpha_daily * factor

    correlation = _safe_ratio(covariance, _std(sr) * _std(br))
    tracking_error = _std(excess) * _d(sqrt(selected.annualization_factor))
    information = _safe_ratio(_mean(excess) * factor, tracking_error)

    up_pairs = [(s, b) for s, b in zip(sr, br) if b > ZERO]
    down_pairs = [(s, b) for s, b in zip(sr, br) if b < ZERO]
    upside = ZERO if not up_pairs else _safe_ratio(_mean([x[0] for x in up_pairs]), _mean([x[1] for x in up_pairs])) * Decimal("100")
    downside_capture = ZERO if not down_pairs else _safe_ratio(_mean([x[0] for x in down_pairs]), _mean([x[1] for x in down_pairs])) * Decimal("100")

    metrics = AdvancedMetrics(
        strategy_total_return_pct=_q(strategy_total * Decimal("100")),
        benchmark_total_return_pct=_q(benchmark_total * Decimal("100")),
        excess_total_return_pct=_q((strategy_total - benchmark_total) * Decimal("100")),
        strategy_cagr_pct=_q(strategy_cagr * Decimal("100")),
        benchmark_cagr_pct=_q(benchmark_cagr * Decimal("100")),
        annualized_volatility_pct=_q(volatility * Decimal("100")),
        sharpe_ratio=_q(sharpe),
        sortino_ratio=_q(sortino),
        max_drawdown_pct=_q(max_dd * Decimal("100")),
        max_drawdown_duration=max_duration,
        calmar_ratio=_q(calmar),
        mar_ratio=_q(mar),
        alpha_pct=_q(alpha * Decimal("100")),
        beta=_q(beta),
        correlation=_q(correlation),
        tracking_error_pct=_q(tracking_error * Decimal("100")),
        information_ratio=_q(information),
        upside_capture_pct=_q(upside),
        downside_capture_pct=_q(downside_capture),
    )

    rolling = []
    window = selected.rolling_window
    for end in range(window, len(data)):
        start = end - window
        s_values = strategy_values[start:end + 1]
        b_values = benchmark_values[start:end + 1]
        s_ret = s_values[-1] / s_values[0] - ONE
        b_ret = b_values[-1] / b_values[0] - ONE
        r = _returns(s_values)
        rolling_sharpe = _safe_ratio(_mean(r), _std(r)) * _d(sqrt(selected.annualization_factor))
        rolling.append(RollingSnapshot(
            timestamp=data[end].timestamp,
            strategy_return_pct=_q(s_ret * Decimal("100")),
            benchmark_return_pct=_q(b_ret * Decimal("100")),
            rolling_sharpe=_q(rolling_sharpe),
        ))

    input_hash = _hash({
        "policy": _policy_payload(selected),
        "observations": [_observation_payload(x) for x in data],
    })

    report = PerformanceReport(
        version=VERSION,
        report_id=f"PERF-{input_hash[:16].upper()}",
        policy=selected,
        observations=data,
        metrics=metrics,
        monthly_returns=_group_periods(data, "%Y-%m"),
        yearly_returns=_group_periods(data, "%Y"),
        rolling_snapshots=tuple(rolling),
        input_hash=input_hash,
        report_hash="",
    )
    return replace(report, report_hash=_hash(_report_payload(report)))


def verify_report(report: PerformanceReport) -> bool:
    if report.version != VERSION:
        raise PerformanceError("unsupported report version")
    if not report.report_id.startswith("PERF-"):
        raise PerformanceError("invalid report ID")
    if len(report.observations) < 3:
        raise PerformanceError("insufficient observations")
    if report.metrics.max_drawdown_pct > ZERO:
        raise PerformanceError("maximum drawdown cannot be positive")
    if report.metrics.max_drawdown_duration < 0:
        raise PerformanceError("drawdown duration cannot be negative")
    clean = replace(report, report_hash="")
    if report.report_hash != _hash(_report_payload(clean)):
        raise PerformanceError("performance report hash mismatch")
    return True


def save_report(report: PerformanceReport, path: str | Path) -> Path:
    verify_report(report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_report_payload(report, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_report(path: str | Path) -> PerformanceReport:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    pol = p["policy"]
    policy = PerformancePolicy(
        annualization_factor=int(pol["annualization_factor"]),
        risk_free_rate_pct=_d(pol["risk_free_rate_pct"]),
        rolling_window=int(pol["rolling_window"]),
    )
    observations = tuple(
        EquityObservation(x["timestamp"], _d(x["strategy_equity"]), _d(x["benchmark_equity"]))
        for x in p["observations"]
    )
    m = p["metrics"]
    metrics = AdvancedMetrics(
        strategy_total_return_pct=_d(m["strategy_total_return_pct"]),
        benchmark_total_return_pct=_d(m["benchmark_total_return_pct"]),
        excess_total_return_pct=_d(m["excess_total_return_pct"]),
        strategy_cagr_pct=_d(m["strategy_cagr_pct"]),
        benchmark_cagr_pct=_d(m["benchmark_cagr_pct"]),
        annualized_volatility_pct=_d(m["annualized_volatility_pct"]),
        sharpe_ratio=_d(m["sharpe_ratio"]),
        sortino_ratio=_d(m["sortino_ratio"]),
        max_drawdown_pct=_d(m["max_drawdown_pct"]),
        max_drawdown_duration=int(m["max_drawdown_duration"]),
        calmar_ratio=_d(m["calmar_ratio"]),
        mar_ratio=_d(m["mar_ratio"]),
        alpha_pct=_d(m["alpha_pct"]),
        beta=_d(m["beta"]),
        correlation=_d(m["correlation"]),
        tracking_error_pct=_d(m["tracking_error_pct"]),
        information_ratio=_d(m["information_ratio"]),
        upside_capture_pct=_d(m["upside_capture_pct"]),
        downside_capture_pct=_d(m["downside_capture_pct"]),
    )
    periods = lambda rows: tuple(
        PeriodReturn(x["period"], _d(x["strategy_return_pct"]), _d(x["benchmark_return_pct"]), _d(x["excess_return_pct"]))
        for x in rows
    )
    rolling = tuple(
        RollingSnapshot(x["timestamp"], _d(x["strategy_return_pct"]), _d(x["benchmark_return_pct"]), _d(x["rolling_sharpe"]))
        for x in p["rolling_snapshots"]
    )
    report = PerformanceReport(
        version=p["version"],
        report_id=p["report_id"],
        policy=policy,
        observations=observations,
        metrics=metrics,
        monthly_returns=periods(p["monthly_returns"]),
        yearly_returns=periods(p["yearly_returns"]),
        rolling_snapshots=rolling,
        input_hash=p["input_hash"],
        report_hash=p["report_hash"],
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
