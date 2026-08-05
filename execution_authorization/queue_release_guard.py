from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .queue_release import evaluate_queue_release


def run_queue_release_authorization(
    inspection_result: dict[str, Any],
    queue_state: dict[str, Any],
    release_request: dict[str, Any],
    consumed_release_ids: set[str],
) -> dict[str, Any]:
    evaluation = evaluate_queue_release(
        inspection_result=inspection_result,
        queue_state=queue_state,
        release_request=release_request,
        consumed_release_ids=consumed_release_ids,
    )

    return {
        "stage": "V392.06A",
        "state": (
            "QUEUE_RELEASE_AUTHORIZATION_READY"
            if evaluation["approved"]
            else "QUEUE_RELEASE_AUTHORIZATION_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "queue_release_authorized": evaluation["approved"],
        "release_token_preparation_allowed": evaluation["approved"],
        "queue_mutation_enabled": False,
        "dispatch_execution_allowed": False,
        "automatic_release_enabled": False,
        "replay_protection_enabled": True,
        "fifo_head_only": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_07A_RELEASE_TOKEN_GATE",
    }
