from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from dynamic_live_risk.io import digest

def build(passed:bool,details:dict[str,Any])->dict[str,Any]:
    body={
        "certificate_type":"DYNAMIC_LIVE_RISK_CERTIFICATE",
        "issued_at":datetime.now(timezone.utc).isoformat(),
        "risk_passed":passed,
        "execution_authorized":False,
        "live_submission_authorized":False,
        "actual_live_orders_submitted":0,
        "details_hash":digest(details),
    }
    body["certificate_sha256"]=digest(body)
    return body
