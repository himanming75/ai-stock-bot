from __future__ import annotations
from typing import Any

def stability_score(
    optimized_rows: list[dict[str, Any]],
    control_result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    optimized = [row for row in optimized_rows if row.get("state") == "OPTIMIZED"]
    skipped = len(optimized_rows) - len(optimized)
    largest_drift = float(
        control_result.get("snapshot", {}).get("largest_absolute_drift_pct", 0.0)
    )
    turnover = float(
        control_result.get("turnover_control", {}).get("used_turnover_pct", 0.0)
    )
    projected_cash = float(
        control_result.get("cash_buffer_control", {}).get("projected_cash_pct", 0.0)
    )

    score = 100.0
    score -= min(35.0, largest_drift * 1.5)
    score -= min(25.0, turnover)
    score += min(10.0, max(0.0, projected_cash - 10.0) * 0.2)
    score += min(10.0, skipped * 2.0)
    score = max(0.0, min(100.0, score))

    if score >= 80:
        level = "HIGH"
    elif score >= 60:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "stability_score": round(score, 6),
        "stability_level": level,
        "minimum_required_score": float(policy.get("minimum_stability_score", 50.0)),
        "passed": score >= float(policy.get("minimum_stability_score", 50.0)),
        "optimized_count": len(optimized),
        "skipped_count": skipped,
    }
