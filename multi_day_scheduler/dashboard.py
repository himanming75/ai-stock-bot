from __future__ import annotations
from pathlib import Path
from multi_day_scheduler.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v103_33_to_v103_64/actual/"
        "multi_day_scheduler_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "scheduler_id":result.get("scheduler_id"),
        "scheduled_trading_days":result.get("scheduled_trading_days",[]),
        "queue_summary":result.get("queue_summary",{}),
        "duplicate_analysis":result.get("duplicate_analysis",{}),
        "checkpoint":result.get("checkpoint",{}),
        "resume_supported":result.get("resume_supported"),
        "execution_authorized":False,
        "paper_only":True,
    }
