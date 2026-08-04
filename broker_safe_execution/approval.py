from __future__ import annotations
from datetime import datetime,timezone
from typing import Any
from broker_safe_execution.io import digest

def build_manual_approval_package(
    intents: list[dict[str, Any]],
    validation: dict[str, Any],
) -> dict[str, Any]:
    body={
        "created_at":datetime.now(timezone.utc).isoformat(),
        "intent_ids":[row.get("intent_id") for row in intents],
        "validation_passed":validation.get("passed") is True,
        "manual_approval_required":True,
        "approval_granted":False,
        "approval_token_issued":False,
        "live_execution_authorized":False,
    }
    body["approval_request_hash"]=digest(body)
    return body
