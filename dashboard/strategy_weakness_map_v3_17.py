
from __future__ import annotations

import math

SEVERITY_WEIGHT = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _num(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None


def _issue(
    code,
    category,
    weakness_type,
    severity,
    title,
    evidence,
    meaning,
    next_evidence_needed,
    confidence="HIGH",
):
    return {
        "code": code,
        "category": category,
        "weakness_type": weakness_type,
        "severity": severity,
        "severity_weight": SEVERITY_WEIGHT[severity],
        "confidence": confidence,
        "title": title,
        "evidence": evidence,
        "meaning": meaning,
        "next_evidence_needed": next_evidence_needed,
    }


def _sample_weakness(historical, diagnostics):
    count = int(historical.get("numeric_trade_count") or 0)
    required = int(
        diagnostics.get("minimum_sample_required") or 10
    )

    if count < required:
        return _issue(
            "SAMPLE_SIZE_INSUFFICIENT",
            "SAMPLE",
            "EVIDENCE_GAP",
            "CRITICAL",
            "Canonical sample is below diagnostic minimum",
            {
                "canonical_numeric_trade_count": count,
                "minimum_required": required,
            },
            "Performance conclusions are not statistically supported by the current canonical sample.",
            f"Collect at least {required} canonical numeric trades before treating diagnostics as stable.",
        )

    if count < 20:
        return _issue(
            "SAMPLE_SIZE_EARLY",
            "SAMPLE",
            "EVIDENCE_GAP",
            "HIGH",
            "Canonical sample is still early",
            {
                "canonical_numeric_trade_count": count,
                "preferred_readiness_sample": 20,
            },
            "The sample clears basic diagnostics but is still below the readiness sample target.",
            "Continue canonical Paper collection toward at least 20 trades.",
        )

    return None


def _downside_observability(diagnostics):
    losses = int(diagnostics.get("loss_count") or 0)
    count = int(
        diagnostics.get("canonical_numeric_trade_count") or 0
    )

    if count > 0 and losses == 0:
        return _issue(
            "NO_LOSING_TRADES_OBSERVED",
            "DOWNSIDE",
            "EVIDENCE_GAP",
            "HIGH",
            "Downside behavior is unobserved",
            {
                "canonical_numeric_trade_count": count,
                "loss_count": losses,
            },
            "No losing canonical trade exists, so loss streak, average loss, and downside robustness cannot be validated.",
            "Observe genuine losing canonical trades before drawing downside conclusions.",
        )
    return None


def _diversification_weakness(diagnostics):
    by_symbol = diagnostics.get("by_symbol") or []
    observed = [
        row for row in by_symbol
        if int(row.get("numeric_trade_count") or 0) > 0
    ]
    symbol_count = len(observed)

    if symbol_count <= 1:
        return _issue(
            "SYMBOL_DIVERSIFICATION_LOW",
            "DIVERSIFICATION",
            "EVIDENCE_GAP",
            "HIGH",
            "Cross-symbol evidence is insufficient",
            {
                "observed_symbol_count": symbol_count,
                "symbols": [
                    row.get("name") for row in observed
                ],
            },
            "Results may reflect one symbol rather than a repeatable strategy effect.",
            "Collect canonical trades across at least two independent symbols before cross-symbol conclusions.",
        )

    if symbol_count == 2:
        return _issue(
            "SYMBOL_DIVERSIFICATION_LIMITED",
            "DIVERSIFICATION",
            "EVIDENCE_GAP",
            "MEDIUM",
            "Symbol coverage is limited",
            {
                "observed_symbol_count": symbol_count,
                "symbols": [
                    row.get("name") for row in observed
                ],
            },
            "Some cross-symbol evidence exists, but concentration remains material.",
            "Continue collecting canonical evidence across additional symbols.",
        )

    return None


def _profitability_weakness(historical, diagnostics):
    count = int(historical.get("numeric_trade_count") or 0)
    if count < 10:
        return None

    net = _num(historical.get("net_realized_pnl"))
    pf_raw = historical.get("profit_factor")
    pf = None if pf_raw == "INF" else _num(pf_raw)
    avg = _num(historical.get("average_trade"))

    if net is not None and net <= 0:
        return _issue(
            "NET_PNL_NON_POSITIVE",
            "PROFITABILITY",
            "PERFORMANCE_RISK",
            "CRITICAL",
            "Canonical Net P/L is non-positive",
            {
                "net_realized_pnl": net,
                "profit_factor": pf_raw,
                "average_trade": avg,
            },
            "The observed canonical strategy has not produced positive aggregate realized P/L.",
            "Accumulate more Paper evidence and investigate losing trade patterns before any strategy promotion.",
            confidence="MEDIUM",
        )

    if pf is not None and pf < 1.0:
        return _issue(
            "PROFIT_FACTOR_BELOW_ONE",
            "PROFITABILITY",
            "PERFORMANCE_RISK",
            "CRITICAL",
            "Profit Factor is below 1",
            {
                "profit_factor": pf,
                "net_realized_pnl": net,
            },
            "Observed gross losses exceed gross profits.",
            "Investigate exit reasons, losing symbols, and stress sensitivity before promotion.",
            confidence="MEDIUM",
        )

    if pf is not None and pf < 1.5:
        return _issue(
            "PROFIT_FACTOR_THIN",
            "PROFITABILITY",
            "PERFORMANCE_RISK",
            "HIGH",
            "Profit Factor margin is thin",
            {
                "profit_factor": pf,
                "net_realized_pnl": net,
            },
            "The observed profit margin may be vulnerable to friction and adverse execution.",
            "Continue Paper validation and compare stressed Profit Factor before promotion.",
            confidence="MEDIUM",
        )

    return None


def _drawdown_weakness(historical):
    count = int(historical.get("numeric_trade_count") or 0)
    if count < 10:
        return None

    drawdown = _num(historical.get("max_realized_drawdown"))
    net = _num(historical.get("net_realized_pnl"))

    if drawdown is None or net is None:
        return None

    base = abs(net) if net != 0 else 1.0
    ratio = drawdown / base

    if ratio >= 1.0:
        severity = "CRITICAL"
    elif ratio >= 0.5:
        severity = "HIGH"
    elif ratio >= 0.25:
        severity = "MEDIUM"
    else:
        return None

    return _issue(
        "REALIZED_DRAWDOWN_ELEVATED",
        "RISK",
        "PERFORMANCE_RISK",
        severity,
        "Realized drawdown is elevated versus Net P/L",
        {
            "max_realized_drawdown": drawdown,
            "net_realized_pnl": net,
            "drawdown_to_net_ratio": ratio,
        },
        "Observed downside is large relative to accumulated realized profit.",
        "Collect more trades and inspect the trades contributing to the drawdown sequence.",
        confidence="MEDIUM",
    )


def _stress_weakness(stress):
    scenarios = stress.get("scenarios") or []
    if not scenarios:
        return _issue(
            "STRESS_RESULTS_UNAVAILABLE",
            "STRESS",
            "EVIDENCE_GAP",
            "HIGH",
            "Stress evidence is unavailable",
            {},
            "No stress scenario results are available for weakness assessment.",
            "Restore or collect canonical trades required by the V3.14 stress layer.",
        )

    if stress.get("sample_status") != "PASS_SAMPLE":
        return _issue(
            "STRESS_SAMPLE_INSUFFICIENT",
            "STRESS",
            "EVIDENCE_GAP",
            "HIGH",
            "Stress conclusions are sample-limited",
            {
                "canonical_numeric_trade_count": stress.get(
                    "canonical_numeric_trade_count"
                ),
                "minimum_interpretation_sample": stress.get(
                    "minimum_interpretation_sample"
                ),
            },
            "Stress transformations can be calculated, but their strategy-level interpretation is not yet reliable.",
            "Reach the stress interpretation sample before treating scenario degradation as stable.",
        )

    severe = None
    baseline = None
    for row in scenarios:
        scenario_id = (
            row.get("scenario") or {}
        ).get("id")
        if scenario_id == "BASELINE":
            baseline = row
        if scenario_id == "SEVERE":
            severe = row

    if not severe or not baseline:
        return None

    severe_pnl = _num(
        (severe.get("stats") or {}).get(
            "net_realized_pnl"
        )
    )
    baseline_pnl = _num(
        (baseline.get("stats") or {}).get(
            "net_realized_pnl"
        )
    )

    if severe_pnl is not None and severe_pnl <= 0:
        return _issue(
            "SEVERE_STRESS_PNL_FAILURE",
            "STRESS",
            "PERFORMANCE_RISK",
            "CRITICAL",
            "Severe stress drives Net P/L non-positive",
            {
                "baseline_net_pnl": baseline_pnl,
                "severe_net_pnl": severe_pnl,
                "severe_degradation_pct": stress.get(
                    "severe_degradation_pct"
                ),
            },
            "The observed strategy loses its realized edge under the severe stress assumptions.",
            "Inspect friction sensitivity and the specific trades that flip under stress.",
            confidence="MEDIUM",
        )

    degradation = _num(
        stress.get("severe_degradation_pct")
    )
    if degradation is not None and degradation >= 0.75:
        return _issue(
            "SEVERE_STRESS_DEGRADATION_HIGH",
            "STRESS",
            "PERFORMANCE_RISK",
            "HIGH",
            "Severe stress materially degrades P/L",
            {
                "severe_degradation_pct": degradation,
                "baseline_net_pnl": baseline_pnl,
                "severe_net_pnl": severe_pnl,
            },
            "Most of the observed edge disappears under severe stress assumptions.",
            "Continue Paper validation and compare real execution friction to the stress boundary.",
            confidence="MEDIUM",
        )

    return None


def _robustness_weakness(robustness):
    sample_status = robustness.get("sample_status")

    if sample_status != "PASS_SAMPLE":
        return _issue(
            "ROBUSTNESS_SAMPLE_INSUFFICIENT",
            "ROBUSTNESS",
            "EVIDENCE_GAP",
            "HIGH",
            "Robustness score is sample-capped",
            {
                "robustness_score": robustness.get(
                    "robustness_score"
                ),
                "raw_robustness_score": robustness.get(
                    "raw_robustness_score"
                ),
                "canonical_numeric_trade_count": robustness.get(
                    "canonical_numeric_trade_count"
                ),
            },
            "Failure boundaries are descriptive only because the canonical sample is below the interpretation minimum.",
            "Collect enough canonical trades to remove the V3.15 sample cap.",
        )

    score = _num(robustness.get("robustness_score"))
    if score is None:
        return None

    if score < 30:
        severity = "CRITICAL"
    elif score < 50:
        severity = "HIGH"
    elif score < 65:
        severity = "MEDIUM"
    else:
        return None

    return _issue(
        "ROBUSTNESS_SCORE_LOW",
        "ROBUSTNESS",
        "PERFORMANCE_RISK",
        severity,
        "Observed robustness score is low",
        {
            "robustness_score": score,
            "failure_boundaries": robustness.get(
                "failure_boundaries"
            ),
        },
        "The observed edge fails after relatively limited adverse transformations.",
        "Inspect the smallest failure boundary before any strategy promotion.",
        confidence="MEDIUM",
    )


def _regime_weakness(regime):
    coverage = regime.get("coverage") or {}
    direction = _num(
        coverage.get("direction_coverage")
    ) or 0.0
    volatility = _num(
        coverage.get("volatility_coverage")
    ) or 0.0

    if regime.get("evidence_trade_count", 0) == 0:
        return _issue(
            "REGIME_EVIDENCE_UNOBSERVED",
            "REGIME",
            "EVIDENCE_GAP",
            "HIGH",
            "Market-regime behavior is unobserved",
            {
                "evidence_trade_count": 0,
                "direction_coverage": direction,
                "volatility_coverage": volatility,
                "regime_status": regime.get("status"),
            },
            "The system cannot determine whether performance changes across Bull, Bear, Sideways, or volatility environments.",
            "Collect canonical trades with explicit regime metadata; do not infer regimes from entry/exit price movement.",
        )

    minimum_coverage = min(direction, volatility)
    if minimum_coverage < 0.5:
        return _issue(
            "REGIME_COVERAGE_LOW",
            "REGIME",
            "EVIDENCE_GAP",
            "HIGH",
            "Market-regime coverage is low",
            {
                "direction_coverage": direction,
                "volatility_coverage": volatility,
                "evidence_trade_count": regime.get(
                    "evidence_trade_count"
                ),
            },
            "A large portion of canonical trades lacks explicit regime evidence.",
            "Increase explicit regime metadata coverage before regime-specific conclusions.",
        )

    if minimum_coverage < 0.8:
        return _issue(
            "REGIME_COVERAGE_PARTIAL",
            "REGIME",
            "EVIDENCE_GAP",
            "MEDIUM",
            "Market-regime coverage is partial",
            {
                "direction_coverage": direction,
                "volatility_coverage": volatility,
            },
            "Regime analysis is available but still incomplete.",
            "Continue capturing explicit regime evidence for canonical trades.",
        )

    return None


def _readiness_weakness(readiness):
    status = readiness.get("status")
    blockers = readiness.get("blockers") or []

    if status == "NOT_READY":
        return _issue(
            "READINESS_NOT_READY",
            "READINESS",
            "EVIDENCE_GAP",
            "HIGH",
            "Strategy readiness gate is not satisfied",
            {
                "status": status,
                "overall_score": readiness.get(
                    "overall_score"
                ),
                "blockers": blockers,
            },
            "The current evidence does not support extended Paper readiness.",
            "Clear readiness blockers through additional canonical evidence rather than automatic parameter changes.",
        )

    if status == "EVALUATING":
        return _issue(
            "READINESS_EVALUATING",
            "READINESS",
            "EVIDENCE_GAP",
            "MEDIUM",
            "Strategy remains in evaluation",
            {
                "status": status,
                "overall_score": readiness.get(
                    "overall_score"
                ),
                "blockers": blockers,
            },
            "Evidence is accumulating but readiness remains incomplete.",
            "Continue the planned Paper validation sample.",
        )

    if status == "CONDITIONAL":
        return _issue(
            "READINESS_CONDITIONAL",
            "READINESS",
            "PERFORMANCE_RISK",
            "MEDIUM",
            "Readiness remains conditional",
            {
                "status": status,
                "overall_score": readiness.get(
                    "overall_score"
                ),
                "blockers": blockers,
            },
            "The sample is adequate, but quality metrics have not reached the strongest readiness state.",
            "Investigate the lowest readiness component before promotion.",
            confidence="MEDIUM",
        )

    return None


def _priority_score(issues):
    if not issues:
        return 0.0

    weighted = sum(
        issue["severity_weight"]
        for issue in issues
    )
    maximum = len(issues) * 4.0

    return round(
        min(100.0, weighted / maximum * 100.0),
        2,
    )


def _overall_severity(issues):
    if not issues:
        return "INFO"

    highest = max(
        issue["severity_weight"]
        for issue in issues
    )

    for name, weight in SEVERITY_WEIGHT.items():
        if weight == highest:
            return name

    return "INFO"


def build_strategy_weakness_map(trade_analytics):
    historical = trade_analytics.get("historical") or {}
    diagnostics = (
        trade_analytics.get(
            "performance_diagnostics"
        )
        or {}
    )
    readiness = (
        trade_analytics.get(
            "strategy_readiness"
        )
        or {}
    )
    stress = (
        trade_analytics.get(
            "strategy_stress_test"
        )
        or {}
    )
    robustness = (
        trade_analytics.get(
            "strategy_robustness"
        )
        or {}
    )
    regime = (
        trade_analytics.get(
            "market_regime_analysis"
        )
        or {}
    )

    checks = (
        _sample_weakness(
            historical,
            diagnostics,
        ),
        _downside_observability(
            diagnostics,
        ),
        _diversification_weakness(
            diagnostics,
        ),
        _profitability_weakness(
            historical,
            diagnostics,
        ),
        _drawdown_weakness(
            historical,
        ),
        _stress_weakness(
            stress,
        ),
        _robustness_weakness(
            robustness,
        ),
        _regime_weakness(
            regime,
        ),
        _readiness_weakness(
            readiness,
        ),
    )

    issues = [
        issue for issue in checks
        if issue is not None
    ]

    issues.sort(
        key=lambda item: (
            item["severity_weight"],
            item["weakness_type"]
            == "PERFORMANCE_RISK",
            item["code"],
        ),
        reverse=True,
    )

    by_type = {
        "EVIDENCE_GAP": sum(
            1
            for issue in issues
            if issue["weakness_type"]
            == "EVIDENCE_GAP"
        ),
        "PERFORMANCE_RISK": sum(
            1
            for issue in issues
            if issue["weakness_type"]
            == "PERFORMANCE_RISK"
        ),
    }

    severity_counts = {
        severity: sum(
            1
            for issue in issues
            if issue["severity"] == severity
        )
        for severity in (
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW",
            "INFO",
        )
    }

    top_priorities = issues[:5]

    return {
        "stage": "V3.17_STRATEGY_WEAKNESS_MAP",
        "status": "PASS",
        "overall_severity": _overall_severity(
            issues
        ),
        "priority_score": _priority_score(
            issues
        ),
        "issue_count": len(issues),
        "severity_counts": severity_counts,
        "type_counts": by_type,
        "issues": issues,
        "top_priorities": top_priorities,
        "interpretation": (
            "Weakness items distinguish evidence gaps from observed performance risks. Evidence gaps are not proof that the strategy is bad."
            if issues
            else "No material weakness is detectable from the currently available analytical evidence."
        ),
        "contracts": {
            "diagnostic_only": True,
            "evidence_gap_not_equal_strategy_failure": True,
            "automatic_parameter_change": False,
            "automatic_strategy_change": False,
            "automatic_promotion": False,
            "live_approval": False,
            "broker_network_used": False,
            "broker_write_performed": False,
            "order_submission_performed": False,
            "paper_runtime_modified": False,
            "production_parameter_modified": False,
            "production_selector_modified": False,
            "canonical_runtime_files_modified": False,
            "duplicate_engine_created": False,
        },
    }
