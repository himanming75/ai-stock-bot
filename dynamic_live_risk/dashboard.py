from pathlib import Path
from dynamic_live_risk.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v134_01_to_v136_64/actual/dynamic_live_risk_result.json")
    return {
        "state":r.get("state"),
        "candidate":r.get("candidate",{}),
        "dynamic_sizing":r.get("dynamic_sizing",{}),
        "risk_budget":r.get("risk_budget",{}),
        "exposure_control":r.get("exposure_control",{}),
        "loss_limits":r.get("loss_limits",{}),
        "risk_gate":r.get("risk_gate",{}),
        "actual_live_orders_submitted":0,
    }
