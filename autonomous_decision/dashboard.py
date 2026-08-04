from __future__ import annotations
from pathlib import Path
from autonomous_decision.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v102_33_to_v102_64/actual/"
        "autonomous_decision_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "decision_id": result.get("decision_id"),
        "signals": result.get("signals", {}),
        "conflict_analysis": result.get("conflict_analysis", {}),
        "safety_veto": result.get("safety_veto", {}),
        "confidence": result.get("confidence", {}),
        "autonomous_decision": result.get("autonomous_decision", {}),
        "approval_gate": result.get("approval_gate", {}),
        "execution_authorized": False,
        "paper_only": True,
    }
