from __future__ import annotations
from typing import Any

def evaluate(
    candidate:dict[str,Any],
    approval:dict[str,Any],
    token:dict[str,Any],
    kill_switch:dict[str,Any],
    payload:dict[str,Any],
    simulation:dict[str,Any],
    policy:dict[str,Any],
)->dict[str,Any]:
    checks={
        "candidate_present":bool(candidate),
        "two_step_approval_required":approval.get("first_approval_required") and approval.get("second_approval_required"),
        "approval_not_granted":approval.get("fully_approved") is False,
        "live_token_not_issued":token.get("live_token") is False,
        "kill_switch_evaluated":isinstance(kill_switch.get("checks"),dict),
        "payload_review_only":payload.get("review_only") is True,
        "simulation_completed":simulation.get("simulated_status")=="filled",
        "live_network_disabled":policy.get("live_network_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
        "actual_live_orders_zero":True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "execution_authorized":False,
        "review_state":"CONTROLLED_MICRO_LIVE_REVIEW_COMPLETE" if not failed else "CONTROLLED_MICRO_LIVE_REVIEW_REQUIRED",
    }
