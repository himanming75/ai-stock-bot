from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .dispatch_preparation import evaluate_dispatch_preparation


def run_dispatch_preparation(
    token_gate_result: dict[str, Any],
    proposal: dict[str, Any],
    dispatch_request: dict[str, Any],
    queued_dispatch_ids: set[str],
) -> dict[str, Any]:
    evaluation = evaluate_dispatch_preparation(
        token_gate_result=token_gate_result,
        proposal=proposal,
        dispatch_request=dispatch_request,
        queued_dispatch_ids=queued_dispatch_ids,
    )

    return {
        "stage": "V392.03A",
        "state": (
            "DISPATCH_PREPARATION_GATE_READY"
            if evaluation["approved"]
            else "DISPATCH_PREPARATION_GATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "dispatch_preparation_approved": evaluation["approved"],
        "queue_entry_allowed": evaluation["approved"],
        "dispatch_execution_allowed": False,
        "automatic_dispatch_enabled": False,
        "replay_protection_enabled": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_04A_DISPATCH_QUEUE_GATE",
    }
