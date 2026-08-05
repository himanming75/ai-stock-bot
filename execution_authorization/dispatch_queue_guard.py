from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .dispatch_queue import enqueue_dispatch


def run_dispatch_queue_gate(
    queue_state: dict[str, Any],
    preparation_result: dict[str, Any],
    owner: str,
) -> dict[str, Any]:
    evaluation = enqueue_dispatch(
        queue_state=queue_state,
        preparation_result=preparation_result,
        owner=owner,
    )

    approved = evaluation["approved"]

    return {
        "stage": "V392.04A",
        "state": (
            "DISPATCH_QUEUE_GATE_READY"
            if approved
            else "DISPATCH_QUEUE_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "queue_entry_created": approved,
        "queue_inspection_allowed": approved,
        "dispatch_execution_allowed": False,
        "automatic_dispatch_enabled": False,
        "queue_locking_enabled": True,
        "fifo_enforced": True,
        "duplicate_prevention_enabled": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_05A_QUEUE_INSPECTION_GATE",
    }
