from pathlib import Path
from controlled_micro_live.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v131_01_to_v133_64/actual/controlled_micro_live_result.json")
    return {
        "state":r.get("state"),
        "candidate":r.get("candidate",{}),
        "approval":r.get("manual_approval_request",{}),
        "token":r.get("approval_token_status",{}),
        "kill_switch":r.get("kill_switch",{}),
        "simulation":r.get("execution_simulation",{}),
        "actual_live_orders_submitted":0,
    }
