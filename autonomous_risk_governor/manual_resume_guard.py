from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .manual_resume import evaluate_manual_resume


def run_guard(
    policy_result: dict[str, Any],
    pause_result: dict[str, Any],
    kill_switch_result: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    evaluation = evaluate_manual_resume(
        pause_result=pause_result,
        kill_switch_result=kill_switch_result,
        request=request,
    )

    state = (
        "MANUAL_RESUME_GUARD_APPROVED"
        if evaluation["approved"]
        else "MANUAL_RESUME_GUARD_BLOCKED"
    )

    return {
        "stage": "V391.09A",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_result.get("policy_hash"),
        "pause_result": pause_result,
        "kill_switch_result": kill_switch_result,
        "request": request,
        "evaluation": evaluation,
        "resume_approved": evaluation["approved"],
        "pause_state_after": "RUNNING" if evaluation["approved"] else "PAUSED",
        "risk_operations_allowed": evaluation["risk_operations_allowed"],
        "automatic_resume_enabled": False,
        "manual_resume_required": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_10A_RISK_GOVERNOR_INTEGRATION",
    }
