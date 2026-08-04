from __future__ import annotations
from typing import Any

def make_decision(
    signals: dict[str, Any],
    conflicts: dict[str, Any],
    vetoes: dict[str, Any],
    confidence: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    minimum_act_confidence = float(policy.get("minimum_act_confidence", 75.0))
    minimum_hold_confidence = float(policy.get("minimum_hold_confidence", 50.0))

    if not signals.get("orchestrator_ready"):
        decision = "BLOCK"
        reason = "MASTER_ORCHESTRATOR_NOT_READY"
    elif not vetoes.get("passed"):
        decision = "BLOCK"
        reason = "SAFETY_VETO_ACTIVE"
    elif not conflicts.get("passed"):
        decision = "REVIEW"
        reason = "SIGNAL_CONFLICT_DETECTED"
    elif signals.get("actionable_adjustment_count", 0) <= 0:
        decision = "HOLD"
        reason = "NO_ACTIONABLE_ADJUSTMENTS"
    elif confidence.get("confidence_score", 0.0) >= minimum_act_confidence:
        decision = "ACT"
        reason = "ALL_GATES_PASS_HIGH_CONFIDENCE"
    elif confidence.get("confidence_score", 0.0) >= minimum_hold_confidence:
        decision = "REVIEW"
        reason = "MANUAL_REVIEW_CONFIDENCE_BAND"
    else:
        decision = "HOLD"
        reason = "CONFIDENCE_TOO_LOW"

    return {
        "decision": decision,
        "reason": reason,
        "decision_actionable": decision == "ACT",
        "minimum_act_confidence": minimum_act_confidence,
        "minimum_hold_confidence": minimum_hold_confidence,
    }
