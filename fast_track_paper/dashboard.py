from __future__ import annotations
from pathlib import Path
from fast_track_paper.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v106_33_to_v108_64/actual/"
        "fast_track_paper_result.json"
    )
    return {
        "state":result.get("state","NOT_AVAILABLE"),
        "cycle_id":result.get("cycle_id"),
        "session_date":result.get("session_date"),
        "paper_order_count":result.get("paper_order_count"),
        "filled_count":result.get("filled_count"),
        "partial_fill_count":result.get("partial_fill_count"),
        "not_filled_count":result.get("not_filled_count"),
        "exit_count":result.get("exit_count"),
        "daily_close":result.get("daily_close",{}),
        "analytics":result.get("analytics",{}),
        "actual_orders_submitted":0,
        "paper_only":True,
    }
