from __future__ import annotations

def optimization_score(
    full_result: dict,
    walk_forward: dict,
) -> float:
    value = (
        1.0 * float(full_result.get("total_return_pct", 0.0))
        - 0.8 * float(full_result.get("maximum_drawdown_pct", 0.0))
        + 4.0 * float(full_result.get("sharpe_ratio", 0.0))
        + 0.20 * float(walk_forward.get("positive_window_pct", 0.0))
        + 1.2 * float(walk_forward.get("average_return_pct", 0.0))
        - 0.8 * abs(min(0.0, float(walk_forward.get("worst_return_pct", 0.0))))
        - 0.4 * float(walk_forward.get("worst_drawdown_pct", 0.0))
    )
    return round(value, 4)

def stability_gate(
    full_result: dict,
    walk_forward: dict,
    policy: dict,
) -> dict:
    checks = {
        "minimum_total_trades": (
            int(full_result.get("total_trades", 0))
            >= int(policy.get("minimum_total_trades", 2))
        ),
        "minimum_positive_window_pct": (
            float(walk_forward.get("positive_window_pct", 0.0))
            >= float(policy.get("minimum_positive_window_pct", 50.0))
        ),
        "minimum_average_return_pct": (
            float(walk_forward.get("average_return_pct", 0.0))
            >= float(policy.get("minimum_average_return_pct", 0.0))
        ),
        "maximum_worst_drawdown_pct": (
            float(walk_forward.get("worst_drawdown_pct", 0.0))
            <= float(policy.get("maximum_worst_drawdown_pct", 35.0))
        ),
        "minimum_full_sharpe": (
            float(full_result.get("sharpe_ratio", 0.0))
            >= float(policy.get("minimum_full_sharpe", 0.0))
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed": [name for name, passed in checks.items() if not passed],
    }
