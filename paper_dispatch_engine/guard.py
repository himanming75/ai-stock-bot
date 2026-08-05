from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .engine import run_local_paper_dispatch


def run_local_paper_dispatch_guard(
    preparation_result: dict[str, Any],
    dispatch_context: dict[str, Any],
    dispatched_context_ids: set[str],
) -> dict[str, Any]:
    prerequisite_checks = {
        "preparation_stage_valid": preparation_result.get("stage") == "V392.09A",
        "preparation_status_pass": preparation_result.get("status") == "PASS",
        "preparation_ready": (
            preparation_result.get("state")
            == "LOCAL_DISPATCH_ENGINE_PREPARATION_READY"
        ),
        "context_created": preparation_result.get("dispatch_context_created") is True,
        "engine_allowed": (
            preparation_result.get("local_paper_dispatch_engine_allowed") is True
        ),
        "broker_adapter_disabled_upstream": (
            preparation_result.get("broker_adapter_enabled") is False
        ),
        "paper_submission_disabled_upstream": (
            preparation_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled_upstream": (
            preparation_result.get("live_submission_enabled") is False
        ),
    }

    if all(prerequisite_checks.values()):
        evaluation = run_local_paper_dispatch(
            context=dispatch_context,
            dispatched_context_ids=dispatched_context_ids,
        )
    else:
        evaluation = {
            "state": "LOCAL_PAPER_DISPATCH_BLOCKED",
            "approved": False,
            "failed": [
                name for name, passed in prerequisite_checks.items() if not passed
            ],
            "required_action": "DO_NOT_CREATE_SIMULATED_EXECUTION",
            "broker_network_used": False,
            "broker_submission_attempted": False,
            "replay_detected": False,
            "local_order": {},
            "local_order_hash": "",
            "local_execution_id": "",
        }

    approved = all(prerequisite_checks.values()) and evaluation["approved"]

    return {
        "stage": "V392.10A",
        "state": (
            "LOCAL_PAPER_DISPATCH_ENGINE_READY"
            if approved
            else "LOCAL_PAPER_DISPATCH_ENGINE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "prerequisite_checks": prerequisite_checks,
        "evaluation": evaluation,
        "local_dispatch_accepted": approved,
        "paper_execution_simulator_allowed": approved,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "queue_mutation_enabled": False,
        "automatic_dispatch_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_11A_PAPER_EXECUTION_SIMULATOR",
    }
