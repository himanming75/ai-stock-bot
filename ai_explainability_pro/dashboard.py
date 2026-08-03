from __future__ import annotations
from pathlib import Path
from ai_explainability_pro.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v92_01_to_v92_32/actual/"
        "ai_explainability_pro_result.json"
    )
    return {
        "explainability_state": result.get("state", "NOT_AVAILABLE"),
        "strategy_id": result.get("strategy_id"),
        "parameters": result.get("parameters", {}),
        "decision": result.get("decision"),
        "confidence": result.get("confidence", {}),
        "summary": result.get("summary"),
        "selection_reasons": result.get("selection_reasons", []),
        "risk_factors": result.get("risk_factors", []),
        "paper_only": True,
    }
