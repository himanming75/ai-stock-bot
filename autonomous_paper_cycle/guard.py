from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .orchestrator import build_cycle_report


def run_autonomous_paper_cycle(
    risk_result: dict[str, Any],
    authorization_result: dict[str, Any],
    dispatch_result: dict[str, Any],
    simulator_result: dict[str, Any],
    accounting_result: dict[str, Any],
    reconciliation_result: dict[str, Any],
    cycle_id: str,
    completed_cycle_ids: set[str],
) -> dict[str, Any]:
    evaluation = build_cycle_report(
        risk_result=risk_result,
        authorization_result=authorization_result,
        dispatch_result=dispatch_result,
        simulator_result=simulator_result,
        accounting_result=accounting_result,
        reconciliation_result=reconciliation_result,
        cycle_id=cycle_id,
        completed_cycle_ids=completed_cycle_ids,
    )

    approved = evaluation["approved"]

    return {
        "stage": "V392.14A",
        "state": (
            "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_READY"
            if approved
            else "AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "cycle_completed": approved,
        "final_qualification_allowed": approved,
        "single_cycle_replay_protection_enabled": True,
        "fail_closed_enabled": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_15A_FULLY_AUTONOMOUS_PAPER_TRADING_QUALIFICATION",
    }
