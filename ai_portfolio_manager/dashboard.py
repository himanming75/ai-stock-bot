from __future__ import annotations
from pathlib import Path
from ai_portfolio_manager.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v99_01_to_v99_32/actual/ai_portfolio_manager_result.json"
    )
    return {
        "portfolio_state":result.get("state","NOT_AVAILABLE"),
        "portfolio_id":result.get("portfolio_id"),
        "candidate_count":result.get("candidate_count",0),
        "champion":result.get("champion"),
        "allocation":result.get("allocation",{}),
        "risk":result.get("risk",{}),
        "paper_only":True,
    }
