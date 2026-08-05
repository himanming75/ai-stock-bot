from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .accounting import apply_fill


def run_fill_accounting(
    simulator_result: dict[str, Any],
    fill_event: dict[str, Any],
    portfolio_state: dict[str, Any],
    applied_fill_event_ids: set[str],
) -> dict[str, Any]:
    prerequisite_checks = {
        "simulator_stage_valid": simulator_result.get("stage") == "V392.11A",
        "simulator_status_pass": simulator_result.get("status") == "PASS",
        "simulator_ready": (
            simulator_result.get("state") == "PAPER_EXECUTION_SIMULATOR_READY"
        ),
        "simulated_fill_created": (
            simulator_result.get("simulated_fill_created") is True
        ),
        "fill_accounting_allowed": (
            simulator_result.get("fill_accounting_allowed") is True
        ),
        "broker_network_disabled": (
            simulator_result.get("broker_network_enabled") is False
        ),
        "paper_submission_disabled": (
            simulator_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled": (
            simulator_result.get("live_submission_enabled") is False
        ),
    }

    if all(prerequisite_checks.values()):
        evaluation = apply_fill(
            portfolio_state=portfolio_state,
            fill_event=fill_event,
            applied_fill_event_ids=applied_fill_event_ids,
        )
    else:
        evaluation = {
            "state": "FILL_ACCOUNTING_BLOCKED",
            "approved": False,
            "checks": {},
            "failed": [
                name for name, passed in prerequisite_checks.items() if not passed
            ],
            "replay_detected": False,
            "portfolio_state": portfolio_state,
            "portfolio_hash": "",
            "accounting_event": {},
            "accounting_event_hash": "",
            "required_action": "DO_NOT_UPDATE_PORTFOLIO",
        }

    approved = all(prerequisite_checks.values()) and evaluation["approved"]

    return {
        "stage": "V392.12A",
        "state": (
            "FILL_ACCOUNTING_POSITION_UPDATE_READY"
            if approved
            else "FILL_ACCOUNTING_POSITION_UPDATE_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "prerequisite_checks": prerequisite_checks,
        "evaluation": evaluation,
        "portfolio_updated": approved,
        "portfolio_reconciliation_allowed": approved,
        "partial_fill_accounting_supported": True,
        "average_cost_supported": True,
        "realized_pnl_supported": True,
        "unrealized_pnl_supported": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_13A_PAPER_PORTFOLIO_RECONCILIATION",
    }
