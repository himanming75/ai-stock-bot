from __future__ import annotations
from typing import Any

def evaluate_gateway(
    limits:dict[str,Any],
    approval:dict[str,Any],
    token:dict[str,Any],
    policy:dict[str,Any],
)->dict[str,Any]:
    checks={
        "micro_limits_passed":limits.get("passed") is True,
        "two_step_approval_complete":approval.get("fully_approved") is True,
        "approval_token_valid":token.get("token_valid") is True,
        "approval_token_unused":token.get("token_used") is False,
        "live_network_enabled":policy.get("live_network_enabled") is True,
        "live_submission_enabled":policy.get("live_submission_enabled") is True,
        "kill_switch_clear":policy.get("kill_switch_clear") is True,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "authorized":False,
        "checks":checks,
        "failed":failed,
        "gateway_state":"HARD_BLOCKED",
        "real_live_network_attempted":False,
        "real_live_submission_attempted":False,
        "actual_live_orders_submitted":0,
    }
