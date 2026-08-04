from __future__ import annotations
from typing import Any

CYCLE_STEPS = [
    "VALIDATE_SOURCE_DECISION",
    "ACQUIRE_CYCLE_LOCK",
    "CREATE_CYCLE_CHECKPOINT",
    "EVALUATE_APPROVAL_REQUIREMENT",
    "PREPARE_PAPER_ACTION_PLAN",
    "FINALIZE_CYCLE_STATE",
]

def initial_steps() -> list[dict[str, Any]]:
    return [
        {
            "step_number": index,
            "step_id": step_id,
            "state": "PENDING",
            "attempt_count": 0,
            "error": None,
        }
        for index, step_id in enumerate(CYCLE_STEPS, start=1)
    ]
