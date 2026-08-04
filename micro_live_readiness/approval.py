from __future__ import annotations
from datetime import datetime,timezone,timedelta
from typing import Any
from micro_live_readiness.io import digest

def create_request(candidates:list[dict[str,Any]],limits:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    created=datetime.now(timezone.utc)
    expires=created+timedelta(minutes=int(policy.get("approval_expiry_minutes",10)))
    body={
        "created_at":created.isoformat(),
        "expires_at":expires.isoformat(),
        "candidate_ids":[c.get("candidate_id") for c in candidates],
        "limits_passed":limits.get("passed") is True,
        "first_approval_required":True,
        "second_approval_required":True,
        "first_approval_granted":False,
        "second_approval_granted":False,
        "approval_token_issued":False,
        "single_use":True,
    }
    body["approval_request_id"]=digest(body)[:24]
    return body

def evaluate_request(request:dict[str,Any])->dict[str,Any]:
    return {
        "approval_request_id":request.get("approval_request_id"),
        "valid":request.get("limits_passed") is True,
        "fully_approved":False,
        "approval_token_issued":False,
        "state":"WAITING_FOR_TWO_STEP_MANUAL_APPROVAL" if request.get("limits_passed") else "APPROVAL_BLOCKED_BY_LIMITS",
    }
