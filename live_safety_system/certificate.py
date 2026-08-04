from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from live_safety_system.io import digest

def build_certificate(
    safety_passed: bool,
    kill_switch: dict[str, Any],
    emergency: dict[str, Any],
    resume: dict[str, Any],
) -> dict[str, Any]:
    body={
        "certificate_type":"LIVE_SAFETY_CERTIFICATE",
        "issued_at":datetime.now(timezone.utc).isoformat(),
        "safety_passed":safety_passed,
        "kill_switch_state":kill_switch.get("state"),
        "emergency_state":emergency.get("state"),
        "resume_state":resume.get("state"),
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "manual_approval_required":True,
        "actual_orders_submitted":0,
    }
    body["certificate_sha256"]=digest(body)
    return body
