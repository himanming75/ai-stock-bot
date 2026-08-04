from __future__ import annotations
from pathlib import Path
from autonomous_paper_operations.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v109_01_to_v110_64/actual/"
        "autonomous_paper_operations_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "operations_id":result.get("operations_id"),
        "tournament":result.get("tournament",{}),
        "operations_report":result.get("operations_report",{}),
        "sessions":result.get("sessions",[]),
        "windows_task_installed":False,
        "actual_orders_submitted":0,
        "paper_only":True,
    }
