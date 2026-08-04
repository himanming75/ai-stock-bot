from __future__ import annotations
from typing import Any

BLOCKED_ACTIONS=[
    "submit_order",
    "cancel_order",
    "replace_order",
    "close_position",
    "close_all_positions",
    "transfer_funds",
]

def evaluate_gateway(
    approval: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    checks={
        "manual_approval_required":approval.get(
            "manual_approval_required"
        ) is True,
        "approval_not_granted":approval.get("approval_granted") is False,
        "approval_token_not_issued":approval.get(
            "approval_token_issued"
        ) is False,
        "live_execution_not_authorized":approval.get(
            "live_execution_authorized"
        ) is False,
        "network_disabled":policy.get(
            "external_network_enabled"
        ) is False,
        "submission_disabled":policy.get(
            "broker_submission_enabled"
        ) is False,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "blocked_actions":BLOCKED_ACTIONS,
        "gateway_state":"HARD_BLOCKED",
        "network_requests_executed":0,
        "write_requests_executed":0,
        "actual_orders_submitted":0,
    }
