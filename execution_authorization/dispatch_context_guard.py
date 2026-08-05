from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .dispatch_context import build_dispatch_context


def run_dispatch_engine_preparation(
    release_gate_result: dict[str, Any],
    preparation_result: dict[str, Any],
    existing_context_ids: set[str],
) -> dict[str, Any]:
    evaluation = build_dispatch_context(
        release_gate_result=release_gate_result,
        preparation_result=preparation_result,
        existing_context_ids=existing_context_ids,
    )

    return {
        "stage": "V392.09A",
        "state": (
            "LOCAL_DISPATCH_ENGINE_PREPARATION_READY"
            if evaluation["approved"]
            else "LOCAL_DISPATCH_ENGINE_PREPARATION_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "dispatch_context_created": evaluation["approved"],
        "local_paper_dispatch_engine_allowed": evaluation["approved"],
        "broker_adapter_enabled": False,
        "queue_mutation_enabled": False,
        "dispatch_execution_allowed": False,
        "automatic_dispatch_enabled": False,
        "replay_protection_enabled": True,
        "paper_endpoint_only": True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_10A_LOCAL_PAPER_DISPATCH_ENGINE",
    }
