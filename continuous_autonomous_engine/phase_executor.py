from __future__ import annotations
from typing import Any

def execute_phase(
    phase: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    item=dict(phase)
    item["attempt_count"]=int(item.get("attempt_count",0))+1
    phase_id=item["phase_id"]

    requirements = {
        "LOAD_SCHEDULER_STATE": context.get("sources_valid"),
        "SELECT_NEXT_SESSION": context.get("session_available"),
        "VALIDATE_AUTONOMOUS_CYCLE": context.get("cycle_valid"),
        "VALIDATE_DECISION_GATE": context.get("decision_valid"),
        "VALIDATE_RISK_AND_REBALANCE": context.get("risk_rebalance_valid"),
        "PREPARE_PAPER_EXECUTION_CONTEXT": context.get("paper_context_valid"),
        "PERSIST_ENGINE_CHECKPOINT": context.get("checkpoint_enabled"),
        "FINALIZE_ENGINE_ITERATION": context.get("final_state_resolved"),
    }

    passed = requirements.get(phase_id) is True
    item["state"]="COMPLETED" if passed else "FAILED"
    item["error"]=None if passed else f"{phase_id}_FAILED"
    return item
