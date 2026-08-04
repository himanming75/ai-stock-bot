from __future__ import annotations
from typing import Any

def evaluate_vetoes(
    signals: dict[str, Any],
    conflicts: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    vetoes = []
    if not signals.get("orchestrator_ready"):
        vetoes.append("ORCHESTRATOR_NOT_READY")
    if not signals.get("risk_gate_passed"):
        vetoes.append("AI_RISK_GATE_FAILED")
    if not signals.get("risk_budget_gate_passed"):
        vetoes.append("RISK_BUDGET_GATE_FAILED")
    if not signals.get("adaptive_gate_passed"):
        vetoes.append("ADAPTIVE_OPTIMIZATION_GATE_FAILED")
    if signals.get("risk_score", 100.0) > float(
        policy.get("maximum_risk_score", 70.0)
    ):
        vetoes.append("RISK_SCORE_LIMIT_EXCEEDED")
    if signals.get("stability_score", 0.0) < float(
        policy.get("minimum_stability_score", 50.0)
    ):
        vetoes.append("STABILITY_SCORE_TOO_LOW")
    if conflicts.get("conflict_count", 0) > int(
        policy.get("maximum_allowed_conflicts", 0)
    ):
        vetoes.append("CONFLICT_LIMIT_EXCEEDED")
    return {
        "veto_count": len(vetoes),
        "vetoes": vetoes,
        "passed": not vetoes,
    }
