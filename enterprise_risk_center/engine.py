from __future__ import annotations
from pathlib import Path
from typing import Any

from enterprise_risk_center.io import load_json, digest_payload
from enterprise_risk_center.statistics import (
    pct_returns,
    historical_var,
    expected_shortfall,
    annualized_volatility,
    max_drawdown,
    rolling_drawdown,
    rolling_volatility,
)
from enterprise_risk_center.stress import run_stress_scenarios
from enterprise_risk_center.monte_carlo import simulate
from enterprise_risk_center.guards import (
    daily_loss_guard,
    concentration_guard,
    volatility_guard,
)

def extract_equity_curve(
    optimizer_result: dict[str, Any],
) -> list[float]:
    candidate = (
        optimizer_result.get("best_stable_candidate")
        or optimizer_result.get("best_candidate")
        or {}
    )
    curve = candidate.get("full_result", {}).get("equity_curve", [])
    return [
        float(value)
        for value in curve
        if isinstance(value, (int, float))
    ]

def evaluate(root: Path) -> dict[str, Any]:
    optimizer = load_json(
        root / "release/v91_33_to_v91_64/actual/"
        "parameter_optimization_result.json"
    )
    portfolio = load_json(
        root / "release/v89_33_to_v89_64/actual/"
        "portfolio_optimization_result.json"
    )
    explainability = load_json(
        root / "release/v92_01_to_v92_32/actual/"
        "ai_explainability_pro_result.json"
    )
    policy = load_json(
        root / "release/v92_33_to_v92_64/input/"
        "enterprise_risk_policy.json"
    )

    curve = extract_equity_curve(optimizer)
    if not curve:
        return {
            "stage": "V92.64",
            "stage_range": "V92.33-V92.64",
            "state": "ENTERPRISE_RISK_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    returns = pct_returns(curve)
    confidence = float(policy.get("var_confidence", 0.95))
    var_pct = historical_var(returns, confidence)
    es_pct = expected_shortfall(returns, confidence)
    volatility_pct = annualized_volatility(returns)
    drawdown_pct = max_drawdown(curve)
    rolling_dd = rolling_drawdown(curve)
    rolling_vol = rolling_volatility(
        returns,
        int(policy.get("rolling_volatility_window", 20)),
    )

    portfolio_data = portfolio.get("portfolio_optimization", {})
    allocations = portfolio_data.get("allocations", [])
    portfolio_value = curve[-1]
    daily_return_pct = returns[-1] * 100.0 if returns else 0.0
    daily_loss = min(0.0, daily_return_pct)

    guards = {
        "daily_loss": daily_loss_guard(daily_loss, policy),
        "concentration": concentration_guard(allocations, policy),
        "volatility": volatility_guard(volatility_pct, policy),
    }
    stress = run_stress_scenarios(
        portfolio_value,
        volatility_pct,
        allocations,
    )
    monte_carlo = simulate(
        returns,
        portfolio_value,
        int(policy.get("monte_carlo_iterations", 1000)),
        int(policy.get("monte_carlo_horizon_days", 20)),
    )

    maximum_var = float(policy.get("maximum_var_pct", 5.0))
    maximum_es = float(policy.get("maximum_expected_shortfall_pct", 8.0))
    maximum_drawdown = float(policy.get("maximum_drawdown_pct", 35.0))
    maximum_loss_probability = float(
        policy.get("maximum_monte_carlo_loss_probability_pct", 60.0)
    )

    checks = {
        "var_within_limit": var_pct <= maximum_var,
        "expected_shortfall_within_limit": es_pct <= maximum_es,
        "drawdown_within_limit": drawdown_pct <= maximum_drawdown,
        "concentration_within_limit": guards["concentration"]["passed"],
        "volatility_within_limit": guards["volatility"]["passed"],
        "daily_loss_guard_clear": (
            guards["daily_loss"]["state"] != "STOP_REQUIRED"
        ),
        "monte_carlo_loss_probability_within_limit": (
            monte_carlo["loss_probability_pct"] <= maximum_loss_probability
        ),
    }
    failed = [
        name for name, passed in checks.items() if not passed
    ]
    state = (
        "ENTERPRISE_RISK_CENTER_APPROVED"
        if not failed
        else "ENTERPRISE_RISK_CENTER_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V92.64",
        "stage_range": "V92.33-V92.64",
        "state": state,
        "status": "PASS",
        "strategy_id": explainability.get("strategy_id"),
        "parameters": explainability.get("parameters", {}),
        "portfolio_value": round(portfolio_value, 4),
        "risk_metrics": {
            "historical_var_pct": round(var_pct, 4),
            "expected_shortfall_pct": round(es_pct, 4),
            "annualized_volatility_pct": round(volatility_pct, 4),
            "maximum_drawdown_pct": round(drawdown_pct, 4),
            "latest_daily_return_pct": round(daily_return_pct, 4),
            "equity_point_count": len(curve),
            "return_observation_count": len(returns),
        },
        "rolling_analysis": {
            "latest_rolling_drawdown_pct": round(
                rolling_dd[-1] if rolling_dd else 0.0, 4
            ),
            "latest_rolling_volatility_pct": round(
                rolling_vol[-1] if rolling_vol else 0.0, 4
            ),
            "maximum_rolling_volatility_pct": round(
                max(rolling_vol) if rolling_vol else 0.0, 4
            ),
        },
        "guards": guards,
        "stress_scenarios": stress,
        "monte_carlo": monte_carlo,
        "portfolio_allocations": allocations,
        "risk_checks": checks,
        "failed_risk_checks": failed,
        "risk_approved": not failed,
        "policy": policy,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V93_01_MARKET_REGIME_ENGINE",
    }
    body["risk_certificate_sha256"] = digest_payload(body)
    return body
