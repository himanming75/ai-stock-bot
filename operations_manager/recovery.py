from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from operations_manager.io import load_json,write_json

def inspect(root:Path)->dict[str,Any]:
    checkpoint=load_json(root/"release/v137_01_to_v139_64/actual/autonomous_checkpoint.json")
    emergency=load_json(root/"release/v141_01_to_v145_64/control/emergency_stop.json")
    return {
        "checkpoint_present":bool(checkpoint),
        "checkpoint":checkpoint,
        "emergency_stop":emergency,
        "safe_to_resume_paper":bool(checkpoint) and emergency.get("enabled") is False,
        "live_resume_authorized":False,
        "actual_live_orders_submitted":0,
    }

def create_plan(root:Path)->dict[str,Any]:
    state=inspect(root)
    steps=[
        "VERIFY_V140_RELEASE",
        "VERIFY_EMERGENCY_STOP_STATE",
        "VERIFY_ALPACA_PAPER_CREDENTIALS",
        "REFRESH_REAL_PAPER_ACCOUNT",
        "RECONCILE_PAPER_POSITIONS_AND_ORDERS",
        "RUN_REAL_PAPER_SHADOW",
    ]
    result={
        "created_at":datetime.now(timezone.utc).isoformat(),
        "state":state,
        "steps":steps,
        "automatic_order_submission_included":False,
        "live_actions_included":False,
        "actual_live_orders_submitted":0,
    }
    write_json(
        root/"release/v156_01_to_v160_64/actual/recovery_plan.json",
        result,
    )
    return result
