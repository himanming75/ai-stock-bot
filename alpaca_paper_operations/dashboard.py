from pathlib import Path
from alpaca_paper_operations.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(
        root/"release/v121_01_to_v123_64/actual/alpaca_paper_operations_result.json"
    )
    return {
        "state":r.get("state"),"mode":r.get("mode"),
        "account_snapshot":r.get("account_snapshot",{}),
        "position_count":len(r.get("position_snapshot",[])),
        "order_count":len(r.get("order_snapshot",[])),
        "market_open":r.get("clock_snapshot",{}).get("is_open"),
        "submission_gate":r.get("submission_gate",{}),
        "qualification":r.get("qualification",{}),
        "actual_paper_orders_submitted":r.get("actual_paper_orders_submitted",0),
        "actual_live_orders_submitted":0,
    }
