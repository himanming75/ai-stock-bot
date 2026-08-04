from __future__ import annotations
from datetime import datetime,timezone,timedelta
from typing import Any
from controlled_micro_live.io import digest

def build_approval(candidate:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    created=datetime.now(timezone.utc)
    expires=created+timedelta(minutes=int(policy.get("approval_expiry_minutes",5)))
    body={
        "candidate_id":candidate.get("candidate_id"),
        "created_at":created.isoformat(),
        "expires_at":expires.isoformat(),
        "first_approval_required":True,
        "second_approval_required":True,
        "first_approval_granted":False,
        "second_approval_granted":False,
        "fully_approved":False,
        "approval_token_issued":False,
    }
    body["approval_request_id"]=digest(body)[:24]
    return body
