from __future__ import annotations

def evaluate_portfolio_risk(
    allocations: dict[str, float],
    ranked: list[dict],
    policy: dict,
) -> dict:
    max_single = float(policy.get("maximum_single_allocation_pct", 40.0))
    max_drawdown = float(policy.get("maximum_strategy_drawdown_pct", 35.0))
    minimum_approved = int(policy.get("minimum_approved_strategies", 1))

    largest = max(allocations.values(), default=0.0) * 100.0
    approved_count = sum(
        1 for row in ranked if row.get("gate", {}).get("approved") is True
    )
    risky = [
        row.get("strategy")
        for row in ranked
        if float(row.get("maximum_drawdown_pct", 0.0)) > max_drawdown
    ]
    checks = {
        "single_allocation_cap": largest <= max_single,
        "minimum_approved_strategies": approved_count >= minimum_approved,
        "strategy_drawdown_cap": not risky,
        "weights_sum_to_one": abs(sum(allocations.values()) - 1.0) <= 0.0001 if allocations else False,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "failed": [name for name, passed in checks.items() if not passed],
        "largest_allocation_pct": round(largest, 4),
        "approved_strategy_count": approved_count,
        "risky_strategies": risky,
    }
