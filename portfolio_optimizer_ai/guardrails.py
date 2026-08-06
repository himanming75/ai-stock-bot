from __future__ import annotations


def evaluate_guardrails(
    *,
    weights: dict[str, float],
    stress_results: list[dict],
    average_abs_correlation: float,
    max_symbol_weight: float = 0.35,
    max_estimated_drawdown: float = 0.12,
    max_average_correlation: float = 0.85,
    max_stress_risk: float = 0.10,
) -> dict:
    breaches = []

    largest_weight = max(weights.values()) if weights else 0.0
    if largest_weight > max_symbol_weight + 0.000001:
        breaches.append("MAX_SYMBOL_WEIGHT")

    worst_drawdown = max(
        (item["estimated_drawdown"] for item in stress_results),
        default=0.0,
    )
    if worst_drawdown > max_estimated_drawdown:
        breaches.append("MAX_ESTIMATED_DRAWDOWN")

    if average_abs_correlation > max_average_correlation:
        breaches.append("MAX_AVERAGE_CORRELATION")

    worst_risk = max(
        (item["portfolio_risk"] for item in stress_results),
        default=0.0,
    )
    if worst_risk > max_stress_risk:
        breaches.append("MAX_STRESS_RISK")

    return {
        "status": "PASS" if not breaches else "BLOCKED",
        "breaches": breaches,
        "limits": {
            "max_symbol_weight": max_symbol_weight,
            "max_estimated_drawdown": max_estimated_drawdown,
            "max_average_correlation": max_average_correlation,
            "max_stress_risk": max_stress_risk,
        },
        "observed": {
            "largest_candidate_weight": round(largest_weight, 6),
            "worst_estimated_drawdown": round(worst_drawdown, 6),
            "average_absolute_correlation": round(
                average_abs_correlation, 6
            ),
            "worst_stress_risk": round(worst_risk, 6),
        },
        "enforcement_mode": "SIMULATION_ONLY",
        "capital_lock_enabled": False,
        "broker_write_enabled": False,
    }
