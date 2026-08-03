from __future__ import annotations
from pathlib import Path
from decision_orchestrator.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v94_33_to_v94_64/actual/paper_execution_plan.json"
    )
    return {
        "decision_orchestration_state": result.get("state", "NOT_AVAILABLE"),
        "source_paper_decision": result.get("source_paper_decision"),
        "paper_order_plans": result.get("paper_order_plans", []),
        "gates": result.get("gates", {}),
        "pre_execution_checklist": result.get("pre_execution_checklist", []),
        "manual_approval_required": result.get("manual_approval_required", True),
        "execution_authorized": False,
        "paper_only": True,
    }
