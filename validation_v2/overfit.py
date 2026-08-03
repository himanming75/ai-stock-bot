from __future__ import annotations

from typing import Any


def calculate_overfit_risk(
    base_result: dict[str, Any],
    walk_forward: dict[str, Any],
    stress: dict[str, Any],
) -> dict[str, Any]:
    base_return = float(base_result.get("total_return_pct", 0.0))
    wf_return = float(walk_forward.get("average_test_return_pct", 0.0))
    worst_stress = float(stress.get("worst_return_pct", 0.0))
    positive_windows = float(walk_forward.get("positive_window_pct", 0.0))

    degradation = max(0.0, base_return - wf_return)
    stress_degradation = max(0.0, base_return - worst_stress)

    score = 0.0
    if base_return > 0:
        score += min(40.0, degradation / max(base_return, 0.0001) * 40.0)
        score += min(35.0, stress_degradation / max(base_return, 0.0001) * 35.0)
    score += max(0.0, 100.0 - positive_windows) * 0.25
    score = min(100.0, score)

    level = "LOW" if score < 30 else "MEDIUM" if score < 60 else "HIGH"
    return {
        "overfit_risk_score": round(score, 2),
        "overfit_risk_level": level,
        "base_return_pct": round(base_return, 4),
        "walk_forward_average_return_pct": round(wf_return, 4),
        "worst_stress_return_pct": round(worst_stress, 4),
        "positive_window_pct": round(positive_windows, 2),
    }
