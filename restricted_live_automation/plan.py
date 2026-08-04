from __future__ import annotations
from datetime import datetime,timezone
from typing import Any

def build(candidate:dict[str,Any],gate:dict[str,Any])->dict[str,Any]:
    return {
      "created_at":datetime.now(timezone.utc).isoformat(),
      "candidate":candidate,
      "gate_passed":gate.get("passed") is True,
      "mode":"RESTRICTED_LIVE_DRY_RUN_ONLY",
      "workflow":[
        "READ_LIVE_ACCOUNT",
        "READ_LIVE_POSITIONS",
        "READ_OPEN_ORDERS",
        "RECONCILE_DUPLICATES",
        "RECHECK_QUALIFICATION",
        "RECHECK_KILL_SWITCH",
        "RECHECK_APPROVAL_TOKEN",
        "SIMULATE_SINGLE_ORDER",
        "WRITE_DRY_RUN_RECEIPT",
        "STOP_BEFORE_BROKER_WRITE"
      ],
      "broker_submission_step_included":False,
      "execution_authorized":False,
      "actual_live_orders_submitted":0
    }
