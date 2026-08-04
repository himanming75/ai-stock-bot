from __future__ import annotations
from pathlib import Path
from risk_budget.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v100_33_to_v100_64/actual/"
        "risk_budget_allocation_result.json"
    )
    return {
        "risk_budget_state":result.get("state","NOT_AVAILABLE"),
        "risk_budget_id":result.get("risk_budget_id"),
        "risk_budget_allocation":result.get("risk_budget_allocation",{}),
        "dynamic_exposure_control":result.get("dynamic_exposure_control",{}),
        "portfolio_heat":result.get("portfolio_heat",{}),
        "risk_budget_gate":result.get("risk_budget_gate",{}),
        "execution_authorized":False,
        "paper_only":True,
    }
