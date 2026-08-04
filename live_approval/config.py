from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from live_approval.io import load_json,write_json

DEFAULT={
    "live_read_only_enabled":False,
    "qualification_required":True,
    "approval_expiry_minutes":10,
    "two_person_approval_required":False,
    "manual_approval_required":True,
    "maximum_candidate_notional":100.0,
    "maximum_candidate_quantity":1,
    "paper_only":True,
    "live_network_write_enabled":False,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v166_01_to_v170_64/config/live_approval_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    try: expiry=int(value.get("approval_expiry_minutes",0))
    except Exception: expiry=0
    if not 1<=expiry<=60: errors.append("approval_expiry_minutes must be 1-60.")
    try: notional=float(value.get("maximum_candidate_notional",0))
    except Exception: notional=0
    if not 1<=notional<=1000: errors.append("maximum_candidate_notional must be 1-1000.")
    try: quantity=int(value.get("maximum_candidate_quantity",0))
    except Exception: quantity=0
    if not 1<=quantity<=10: errors.append("maximum_candidate_quantity must be 1-10.")
    if value.get("live_network_write_enabled") is not False:
        errors.append("Live network write must remain disabled.")
    if value.get("live_submission_enabled") is not False:
        errors.append("Live submission must remain disabled.")
    if value.get("paper_only") is not True:
        errors.append("Paper-only safety flag must remain enabled.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["approval_expiry_minutes"]=expiry or 10
    normalized["maximum_candidate_notional"]=notional or 100.0
    normalized["maximum_candidate_quantity"]=quantity or 1
    normalized["paper_only"]=True
    normalized["live_network_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
