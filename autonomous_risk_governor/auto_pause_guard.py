from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .auto_pause import evaluate_auto_pause


def run_guard(
    policy_result: dict[str, Any],
    guard_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if policy_result.get("state") != "RISK_POLICY_READY":
        raise ValueError("RISK_POLICY_NOT_READY")
    if policy_result.get("validation", {}).get("valid") is not True:
        raise ValueError("RISK_POLICY_INVALID")

    evaluation = evaluate_auto_pause(guard_results)

    if evaluation["pause_required"]:
        state = "AUTO_PAUSE_GUARD_PAUSED"
    elif evaluation["warning"]:
        state = "AUTO_PAUSE_GUARD_WARNING"
    else:
        state = "AUTO_PAUSE_GUARD_STANDBY"

    return {
        "stage": "V391.08A",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "policy_hash": policy_result.get("policy_hash"),
        "guard_results": guard_results,
        "evaluation": evaluation,
        "pause_state": "PAUSED" if evaluation["pause_required"] else "RUNNING",
        "pause_required": evaluation["pause_required"],
        "risk_operations_allowed": (
            policy_result.get("risk_operations_allowed") is True
            and evaluation["risk_operations_allowed"]
        ),
        "automatic_resume_enabled": False,
        "manual_resume_required": evaluation["manual_resume_required"],
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V391_09A_MANUAL_RESUME",
    }
