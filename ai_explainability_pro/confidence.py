from __future__ import annotations
from typing import Any

def confidence_score(features: dict[str, Any], risks: list[dict[str, Any]]) -> dict[str, Any]:
    score = 50.0
    score += min(20.0, max(0.0, float(features.get("positive_window_pct", 0.0)) - 50.0) * 0.5)
    score += min(15.0, max(0.0, float(features.get("sharpe_ratio", 0.0))) * 5.0)
    score += 10.0 if features.get("stability_passed") else -20.0
    score += min(10.0, int(features.get("total_trades", 0)))
    for risk in risks:
        score -= 12.0 if risk.get("severity") == "high" else 6.0
    score = max(0.0, min(100.0, score))
    level = "HIGH" if score >= 75 else "MEDIUM" if score >= 50 else "LOW"
    return {
        "score": round(score, 2),
        "level": level,
        "basis": "deterministic_rule_based_explanation",
    }
