from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .queue_inspection import inspect_queue


def run_queue_inspection_gate(
    queue_state: dict[str, Any],
    maximum_entry_age_seconds: int = 900,
) -> dict[str, Any]:
    evaluation = inspect_queue(
        queue_state=queue_state,
        maximum_entry_age_seconds=maximum_entry_age_seconds,
    )

    return {
        "stage": "V392.05A",
        "state": (
            "QUEUE_INSPECTION_GATE_READY"
            if evaluation["release_ready"]
            else "QUEUE_INSPECTION_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "queue_release_inspection_passed": evaluation["release_ready"],
        "release_authorization_allowed": evaluation["release_ready"],
        "dispatch_execution_allowed": False,
        "automatic_release_enabled": False,
        "queue_mutation_enabled": False,
        "fifo_enforced": True,
        "queue_hash_verified": evaluation["valid"],
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_06A_QUEUE_RELEASE_AUTHORIZATION",
    }
