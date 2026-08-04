from __future__ import annotations
from typing import Any

def resolve_cycle_state(
    decision_result: dict[str, Any],
) -> dict[str, Any]:
    decision = str(
        decision_result.get("autonomous_decision", {}).get("decision", "BLOCK")
    )
    approval = decision_result.get("approval_gate", {})

    if decision == "ACT":
        state = "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL"
        action = "WAIT_FOR_MANUAL_APPROVAL"
    elif decision == "HOLD":
        state = "AUTONOMOUS_CYCLE_HOLD"
        action = "NO_ACTION"
    elif decision == "REVIEW":
        state = "AUTONOMOUS_CYCLE_REVIEW_REQUIRED"
        action = "SEND_TO_MANUAL_REVIEW"
    else:
        state = "AUTONOMOUS_CYCLE_BLOCKED"
        action = "BLOCK_CYCLE"

    return {
        "state": state,
        "cycle_action": action,
        "decision": decision,
        "approval_eligible": approval.get("approval_eligible") is True,
        "approval_granted": False,
        "execution_authorized": False,
    }
