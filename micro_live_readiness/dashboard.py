from pathlib import Path
from micro_live_readiness.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v127_01_to_v128_64/actual/micro_live_readiness_result.json")
    return {
        "state":r.get("state"),
        "candidate_count":len(r.get("live_order_candidates",[])),
        "eligible_count":r.get("micro_live_limits",{}).get("eligible_count"),
        "approval_state":r.get("manual_approval_status",{}).get("state"),
        "gateway_state":r.get("live_gateway",{}).get("gateway_state"),
        "actual_live_orders_submitted":0,
    }
