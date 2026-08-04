from __future__ import annotations
from typing import Any

def evaluate(gate:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    checks={
        "candidate_gate_passed":gate.get("passed") is True,
        "manual_approval_complete":False,
        "approval_token_valid":False,
        "live_network_write_enabled":policy.get("live_network_write_enabled") is True,
        "live_submission_enabled":policy.get("live_submission_enabled") is True,
    }
    return {
        "authorized":False,
        "checks":checks,
        "failed":[k for k,v in checks.items() if not v],
        "gateway_state":"HARD_BLOCKED",
        "live_read_only_allowed":True,
        "live_write_allowed":False,
        "actual_live_orders_submitted":0,
    }
