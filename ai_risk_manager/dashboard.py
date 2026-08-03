from __future__ import annotations
from pathlib import Path
from ai_risk_manager.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v100_01_to_v100_32/actual/"
        "ai_risk_manager_result.json"
    )
    return {
        "risk_state":result.get("state","NOT_AVAILABLE"),
        "risk_assessment_id":result.get("risk_assessment_id"),
        "exposure":result.get("exposure",{}),
        "value_at_risk":result.get("value_at_risk",{}),
        "drawdown":result.get("drawdown",{}),
        "stress":result.get("stress",{}),
        "risk_score":result.get("risk_score",{}),
        "pre_execution_gate":result.get("pre_execution_gate",{}),
        "execution_authorized":False,
        "paper_only":True,
    }
