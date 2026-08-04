from __future__ import annotations
from pathlib import Path
from master_ai_orchestrator.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v102_01_to_v102_32/actual/"
        "master_ai_orchestrator_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "orchestration_id": result.get("orchestration_id"),
        "module_registry": result.get("module_registry", []),
        "workflow": result.get("workflow", {}),
        "health": result.get("health", {}),
        "safety_lock": result.get("safety_lock", {}),
        "recovery_plan": result.get("recovery_plan", {}),
        "checkpoint": result.get("checkpoint", {}),
        "execution_authorized": False,
        "paper_only": True,
    }
