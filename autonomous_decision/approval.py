from __future__ import annotations
from typing import Any

def build_approval_gate(
    decision: dict[str, Any],
    confidence: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    manual_approval_required = True
    approval_eligible = (
        decision.get("decision") == "ACT"
        and confidence.get("confidence_score", 0.0)
        >= float(policy.get("minimum_act_confidence", 75.0))
    )
    return {
        "manual_approval_required": manual_approval_required,
        "approval_eligible": approval_eligible,
        "approval_granted": False,
        "execution_authorized": False,
        "submission_allowed": False,
    }
