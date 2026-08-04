from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Any
from controlled_micro_live.io import load_json,write_json,digest
from controlled_micro_live.config import load as load_policy

def path(root:Path)->Path:
    return root/"release/v171_01_to_v175_64/actual/micro_live_approval_token.json"

def issue(root:Path,candidate:dict[str,Any],approval:dict[str,Any],qualification_passed:bool)->dict[str,Any]:
    policy=load_policy(root)
    now=datetime.now(timezone.utc)
    eligible=(
        qualification_passed
        and approval.get("approved") is True
        and approval.get("execution_authorized") is False
        and bool(candidate)
    )
    token={
        "token_id":digest({"candidate":candidate,"issued_at":now.isoformat()})[:32],
        "issued_at":now.isoformat(),
        "expires_at":(now+timedelta(minutes=int(policy["approval_token_expiry_minutes"]))).isoformat(),
        "candidate_hash":digest(candidate),
        "eligible":eligible,
        "used":False,
        "execution_authorized":False,
        "actual_live_orders_submitted":0,
    }
    write_json(path(root),token)
    return token

def inspect(root:Path,candidate:dict[str,Any])->dict[str,Any]:
    token=load_json(path(root))
    if not token:return {"valid":False,"reason":"TOKEN_NOT_FOUND"}
    now=datetime.now(timezone.utc)
    try: expired=now>datetime.fromisoformat(token["expires_at"])
    except Exception: expired=True
    valid=(
        token.get("eligible") is True
        and token.get("used") is False
        and not expired
        and token.get("candidate_hash")==digest(candidate)
    )
    return {"valid":valid,"expired":expired,"token":token}
