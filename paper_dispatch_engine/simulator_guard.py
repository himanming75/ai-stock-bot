from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .simulator import simulate_fill


def run_paper_execution_simulator(
    dispatch_result: dict[str, Any],
    local_order: dict[str, Any],
    market_snapshot: dict[str, Any],
    policy: dict[str, Any],
    simulated_execution_ids: set[str],
) -> dict[str, Any]:
    prerequisite_checks = {
        "dispatch_stage_valid": dispatch_result.get("stage") == "V392.10A",
        "dispatch_status_pass": dispatch_result.get("status") == "PASS",
        "dispatch_ready": (
            dispatch_result.get("state") == "LOCAL_PAPER_DISPATCH_ENGINE_READY"
        ),
        "dispatch_accepted": dispatch_result.get("local_dispatch_accepted") is True,
        "simulator_allowed": (
            dispatch_result.get("paper_execution_simulator_allowed") is True
        ),
        "broker_network_disabled": (
            dispatch_result.get("broker_network_enabled") is False
        ),
        "paper_submission_disabled": (
            dispatch_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled": (
            dispatch_result.get("live_submission_enabled") is False
        ),
    }

    if all(prerequisite_checks.values()):
        evaluation = simulate_fill(
            local_order=local_order,
            market_snapshot=market_snapshot,
            policy=policy,
            simulated_execution_ids=simulated_execution_ids,
        )
    else:
        evaluation = {
            "state": "PAPER_EXECUTION_SIMULATION_BLOCKED",
            "approved": False,
            "checks": {},
            "failed": [
                name for name, passed in prerequisite_checks.items() if not passed
            ],
            "replay_detected": False,
            "fill_event": {},
            "fill_event_hash": "",
            "required_action": "DO_NOT_CREATE_FILL_EVENT",
            "actual_broker_orders_submitted": 0,
        }

    approved = all(prerequisite_checks.values()) and evaluation["approved"]

    return {
        "stage": "V392.11A",
        "state": (
            "PAPER_EXECUTION_SIMULATOR_READY"
            if approved
            else "PAPER_EXECUTION_SIMULATOR_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "prerequisite_checks": prerequisite_checks,
        "evaluation": evaluation,
        "simulated_fill_created": approved,
        "fill_accounting_allowed": approved,
        "partial_fill_supported": True,
        "slippage_supported": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_12A_FILL_ACCOUNTING_AND_POSITION_UPDATE",
    }
