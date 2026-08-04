from __future__ import annotations
from typing import Any

def calculate_confidence(
    signals: dict[str, Any],
    conflicts: dict[str, Any],
    vetoes: dict[str, Any],
) -> dict[str, Any]:
    score = 0.0
    score += 20.0 if signals.get("orchestrator_ready") else 0.0
    score += 15.0 if signals.get("meta_risk_approved") else 0.0
    score += 20.0 if signals.get("risk_gate_passed") else 0.0
    score += 15.0 if signals.get("risk_budget_gate_passed") else 0.0
    score += 15.0 if signals.get("adaptive_gate_passed") else 0.0
    score += min(10.0, signals.get("stability_score", 0.0) / 10.0)
    score += min(5.0, signals.get("regime_confidence", 0.0) / 20.0)
    score -= conflicts.get("conflict_count", 0) * 10.0
    score -= vetoes.get("veto_count", 0) * 20.0
    score = max(0.0, min(100.0, score))
    if score >= 80:
        level = "HIGH"
    elif score >= 60:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "confidence_score": round(score, 6),
        "confidence_level": level,
    }
