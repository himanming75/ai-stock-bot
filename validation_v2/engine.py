from __future__ import annotations

import hashlib
import json
from typing import Any

from backtest_v2.engine import run_backtest
from backtest_v2.models import Bar
from validation_v2.monte_carlo import run_monte_carlo
from validation_v2.overfit import calculate_overfit_risk
from validation_v2.stress import run_stress_tests
from validation_v2.walk_forward import run_walk_forward


def digest_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_validation(
    symbol: str,
    bars: list[Bar],
    policy: dict[str, Any],
) -> dict[str, Any]:
    base_policy = policy.get("backtest_policy", {})
    base = run_backtest(symbol, bars, base_policy)
    walk_forward = run_walk_forward(symbol, bars, policy)
    stress = run_stress_tests(symbol, bars, policy)
    monte_carlo = run_monte_carlo(
        base["trades"],
        iterations=int(policy.get("monte_carlo_iterations", 500)),
        seed=int(policy.get("monte_carlo_seed", 8709)),
        initial_equity=float(base.get("initial_cash", 100000.0)),
    )
    overfit = calculate_overfit_risk(base, walk_forward, stress)

    checks = {
        "walk_forward_windows": walk_forward["window_count"] >= int(
            policy.get("minimum_walk_forward_windows", 2)
        ),
        "positive_window_rate": walk_forward["positive_window_pct"] >= float(
            policy.get("minimum_positive_window_pct", 50.0)
        ),
        "stress_return_floor": stress["worst_return_pct"] >= float(
            policy.get("minimum_stress_return_pct", -20.0)
        ),
        "stress_drawdown_cap": stress["worst_drawdown_pct"] <= float(
            policy.get("maximum_stress_drawdown_pct", 35.0)
        ),
        "overfit_risk_cap": overfit["overfit_risk_score"] <= float(
            policy.get("maximum_overfit_risk_score", 60.0)
        ),
        "monte_carlo_loss_probability": (
            monte_carlo["probability_of_loss_pct"]
            <= float(policy.get("maximum_loss_probability_pct", 50.0))
        ),
    }
    robustness_passed = all(checks.values())

    certificate_body = {
        "state": (
            "BACKTEST_ROBUSTNESS_VALIDATED"
            if robustness_passed
            else "BACKTEST_ROBUSTNESS_NOT_VALIDATED"
        ),
        "symbol": symbol,
        "checks": checks,
        "walk_forward_summary": {
            key: value for key, value in walk_forward.items()
            if key != "windows"
        },
        "stress_summary": {
            key: value for key, value in stress.items()
            if key != "scenarios"
        },
        "monte_carlo": monte_carlo,
        "overfit": overfit,
        "paper_only": True,
    }
    certificate = {
        **certificate_body,
        "certificate_sha256": digest_payload(certificate_body),
    }

    return {
        "base_backtest": base,
        "walk_forward": walk_forward,
        "stress": stress,
        "monte_carlo": monte_carlo,
        "overfit": overfit,
        "robustness_checks": checks,
        "robustness_passed": robustness_passed,
        "certificate": certificate,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
