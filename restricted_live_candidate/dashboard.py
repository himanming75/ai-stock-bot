from pathlib import Path
from restricted_live_candidate.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v129_01_to_v130_64/actual/restricted_live_candidate_result.json")
    return {
        "state":r.get("state"),
        "candidate_count":len(r.get("restricted_live_candidates",[])),
        "eligible_count":r.get("restricted_gate",{}).get("eligible_count"),
        "conflict_count":r.get("reconciliation",{}).get("conflict_count"),
        "gateway_state":r.get("live_gateway",{}).get("gateway_state"),
        "actual_live_orders_submitted":0,
    }
