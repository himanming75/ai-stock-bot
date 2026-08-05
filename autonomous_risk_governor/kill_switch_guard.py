from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .kill_switch import evaluate_kill_switch


def run_guard(
    policy_result: dict[str, Any],
    control: dict[str, Any],
) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    policy = policy_result["policy"]

    evaluation = evaluate_kill_switch(
        kill_switch_required=policy.get("kill_switch_required"),
        kill_switch_active=control.get(
            "kill_switch_active",
            policy.get("kill_switch_active", False),
        ),
        manual_resume_required=policy.get("manual_resume_required"),
        automatic_resume_enabled=policy.get("automatic_resume_enabled"),
        risk_operations_allowed=control.get(
            "risk_operations_allowed",
            policy_result.get("risk_operations_allowed", False),
        ),
    )

    if evaluation["state"] == "KILL_SWITCH_ACTIVE":
        state = "KILL_SWITCH_GUARD_BLOCKED"
    elif evaluation["state"] == "KILL_SWITCH_POLICY_INVALID":
        state = "KILL_SWITCH_GUARD_INVALID"
    else:
        state = "KILL_SWITCH_GUARD_STANDBY"

    return {
        "stage": "V391.07A",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_result.get("policy_hash"),
        "control": control,
        "evaluation": evaluation,
        "kill_switch_blocked": not evaluation["effective_risk_operations_allowed"],
        "risk_operations_allowed": evaluation["effective_risk_operations_allowed"],
        "automatic_resume_enabled": False,
        "manual_resume_required": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_08A_AUTO_PAUSE",
    }
