from __future__ import annotations
from typing import Any

PHASES = [
    "LOAD_SCHEDULER_STATE",
    "SELECT_NEXT_SESSION",
    "VALIDATE_AUTONOMOUS_CYCLE",
    "VALIDATE_DECISION_GATE",
    "VALIDATE_RISK_AND_REBALANCE",
    "PREPARE_PAPER_EXECUTION_CONTEXT",
    "PERSIST_ENGINE_CHECKPOINT",
    "FINALIZE_ENGINE_ITERATION",
]

def initial_phases() -> list[dict[str, Any]]:
    return [
        {
            "phase_number": index,
            "phase_id": phase_id,
            "state": "PENDING",
            "attempt_count": 0,
            "error": None,
        }
        for index, phase_id in enumerate(PHASES, start=1)
    ]
