from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .local_dispatch_release import evaluate_local_dispatch_release


def run_local_dispatch_release_gate(
    release_token_result: dict[str, Any],
    queue_state: dict[str, Any],
    released_dispatch_ids: set[str],
) -> dict[str, Any]:
    evaluation = evaluate_local_dispatch_release(
        release_token_result=release_token_result,
        queue_state=queue_state,
        released_dispatch_ids=released_dispatch_ids,
    )

    return {
        "stage": "V392.08A",
        "state": (
            "LOCAL_DISPATCH_RELEASE_GATE_READY"
            if evaluation["approved"]
            else "LOCAL_DISPATCH_RELEASE_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "local_dispatch_release_approved": evaluation["approved"],
        "local_dispatch_engine_preparation_allowed": evaluation["approved"],
        "queue_mutation_enabled": False,
        "dispatch_execution_allowed": False,
        "automatic_dispatch_enabled": False,
        "replay_protection_enabled": True,
        "fifo_head_only": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_09A_LOCAL_DISPATCH_ENGINE_PREPARATION",
    }
