from __future__ import annotations
from typing import Any

def collect_signals(
    orchestrator: dict[str, Any],
    regime: dict[str, Any],
    meta: dict[str, Any],
    risk: dict[str, Any],
    risk_budget: dict[str, Any],
    adaptive: dict[str, Any],
) -> dict[str, Any]:
    return {
        "orchestrator_ready": (
            orchestrator.get("state") == "MASTER_AI_ORCHESTRATOR_READY"
            and orchestrator.get("health", {}).get("passed") is True
            and orchestrator.get("safety_lock", {}).get("passed") is True
        ),
        "primary_regime": regime.get("primary_regime"),
        "regime_confidence": float(regime.get("alignment_pct", 0.0)),
        "regime_conflict": bool(regime.get("conflict_detected", False)),
        "meta_decision": meta.get("paper_decision"),
        "meta_risk_approved": bool(meta.get("risk_approved", False)),
        "selected_strategy_id": meta.get("selected_strategy_id"),
        "risk_gate_passed": (
            risk.get("pre_execution_gate", {}).get("passed") is True
        ),
        "risk_score": float(
            risk.get("risk_score", {}).get("risk_score", 100.0)
        ),
        "risk_level": risk.get("risk_score", {}).get("risk_level"),
        "risk_budget_gate_passed": (
            risk_budget.get("risk_budget_gate", {}).get("passed") is True
        ),
        "target_gross_exposure_pct": float(
            risk_budget.get("dynamic_exposure_control", {}).get(
                "target_gross_exposure_pct", 0.0
            )
        ),
        "adaptive_gate_passed": (
            adaptive.get("optimization_gate", {}).get("passed") is True
        ),
        "adaptive_state": adaptive.get("state"),
        "actionable_adjustment_count": int(
            adaptive.get("actionable_adjustment_count", 0)
        ),
        "stability_score": float(
            adaptive.get("stability", {}).get("stability_score", 0.0)
        ),
    }
