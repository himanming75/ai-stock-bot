from __future__ import annotations
from typing import Any
from controlled_micro_live.io import digest

def issue_simulated_token(approval:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    eligible=(
        approval.get("fully_approved") is True
        and policy.get("simulated_token_issue_enabled") is True
    )
    token_hash=digest({
        "approval_request_id":approval.get("approval_request_id"),
        "candidate_id":approval.get("candidate_id"),
        "single_use":True,
    }) if eligible else None
    return {
        "token_present":eligible,
        "token_hash":token_hash,
        "token_valid":eligible,
        "token_used":False,
        "token_single_use":True,
        "token_expired":False,
        "token_replay_detected":False,
        "live_token":False,
        "simulation_only":True,
    }

def consume_simulated_token(token:dict[str,Any])->dict[str,Any]:
    if token.get("token_used"):
        return {
            **token,
            "consume_allowed":False,
            "token_replay_detected":True,
        }
    if not token.get("token_valid"):
        return {
            **token,
            "consume_allowed":False,
            "token_replay_detected":False,
        }
    return {
        **token,
        "consume_allowed":True,
        "token_used":True,
        "token_valid":False,
        "token_replay_detected":False,
    }
