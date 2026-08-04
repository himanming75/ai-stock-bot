from pathlib import Path
from autonomous_orchestrator.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v137_01_to_v139_64/actual/autonomous_orchestrator_result.json")
    return {
        "state":r.get("state"),
        "market":r.get("market",{}),
        "signal_count":len(r.get("signals",[])),
        "candidate_count":len(r.get("selected_candidates",[])),
        "plan_count":len(r.get("paper_order_plans",[])),
        "paper_orders_submitted":r.get("actual_paper_orders_submitted",0),
        "positions":r.get("positions",[]),
        "performance":r.get("performance",{}),
        "actual_live_orders_submitted":0,
    }
