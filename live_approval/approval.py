from __future__ import annotations
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Any
from live_approval.io import load_json,write_json,append_jsonl,digest
from live_approval.config import load as load_policy

def request_path(root:Path)->Path:
    return root/"release/v166_01_to_v170_64/actual/live_approval_request.json"

def create(root:Path,candidate:dict[str,Any],qualification:dict[str,Any])->dict[str,Any]:
    policy=load_policy(root)
    passed=qualification.get("qualification",{}).get("passed") is True
    quantity=float(candidate.get("quantity",0) or 0)
    notional=float(candidate.get("estimated_notional",0) or 0)
    checks={
        "qualification_passed":passed or not policy.get("qualification_required"),
        "candidate_present":bool(candidate),
        "quantity_within_limit":0<quantity<=policy["maximum_candidate_quantity"],
        "notional_within_limit":0<notional<=policy["maximum_candidate_notional"],
        "manual_approval_required":policy.get("manual_approval_required") is True,
        "live_write_disabled":policy.get("live_network_write_enabled") is False,
        "live_submission_disabled":policy.get("live_submission_enabled") is False,
    }
    failed=[k for k,v in checks.items() if not v]
    now=datetime.now(timezone.utc)
    request={
        "request_id":digest({"candidate":candidate,"created":now.isoformat()})[:24],
        "created_at":now.isoformat(),
        "expires_at":(now+timedelta(minutes=policy["approval_expiry_minutes"])).isoformat(),
        "candidate":candidate,
        "checks":checks,
        "failed":failed,
        "eligible_for_review":not failed,
        "decision":"BLOCKED" if failed else "PENDING",
        "approved":False,
        "rejected":False,
        "execution_authorized":False,
        "actual_live_orders_submitted":0,
    }
    write_json(request_path(root),request)
    append_jsonl(root/"release/v166_01_to_v170_64/actual/approval_ledger.jsonl",{
        "observed_at":now.isoformat(),"event":"REQUEST_CREATED",
        "request_id":request["request_id"],"decision":request["decision"],
        "actual_live_orders_submitted":0,
    })
    return request

def decide(root:Path,decision:str,operator_note:str="")->dict[str,Any]:
    request=load_json(request_path(root))
    if not request:return {"ok":False,"error":"REQUEST_NOT_FOUND"}
    now=datetime.now(timezone.utc)
    try: expired=now>datetime.fromisoformat(request["expires_at"])
    except Exception: expired=True
    normalized=decision.strip().upper()
    if expired:
        normalized="EXPIRED"
    elif normalized not in {"APPROVE","REJECT"}:
        return {"ok":False,"error":"INVALID_DECISION"}
    elif not request.get("eligible_for_review"):
        normalized="BLOCKED"
    request.update({
        "decision":normalized,
        "approved":normalized=="APPROVE",
        "rejected":normalized=="REJECT",
        "operator_note":operator_note,
        "decided_at":now.isoformat(),
        "execution_authorized":False,
        "actual_live_orders_submitted":0,
    })
    write_json(request_path(root),request)
    append_jsonl(root/"release/v166_01_to_v170_64/actual/approval_ledger.jsonl",{
        "observed_at":now.isoformat(),"event":"DECISION",
        "request_id":request.get("request_id"),"decision":normalized,
        "execution_authorized":False,"actual_live_orders_submitted":0,
    })
    return {"ok":True,"request":request}
