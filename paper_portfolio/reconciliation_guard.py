from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .reconciliation import reconcile_portfolio


def run_portfolio_reconciliation(
    accounting_result: dict[str, Any],
    portfolio_state: dict[str, Any],
    accounting_event: dict[str, Any],
    applied_fill_registry: dict[str, Any],
) -> dict[str, Any]:
    prerequisite_checks = {
        "accounting_stage_valid": accounting_result.get("stage") == "V392.12A",
        "accounting_status_pass": accounting_result.get("status") == "PASS",
        "broker_network_disabled": (
            accounting_result.get("broker_network_enabled") is False
        ),
        "paper_submission_disabled": (
            accounting_result.get("paper_submission_enabled") is False
        ),
        "live_submission_disabled": (
            accounting_result.get("live_submission_enabled") is False
        ),
    }

    if all(prerequisite_checks.values()):
        evaluation = reconcile_portfolio(
            portfolio_state=portfolio_state,
            accounting_event=accounting_event,
            applied_fill_registry=applied_fill_registry,
        )
    else:
        evaluation = {
            "state": "PAPER_PORTFOLIO_RECONCILIATION_FAILED",
            "valid": False,
            "checks": {},
            "errors": [
                name for name, passed in prerequisite_checks.items() if not passed
            ],
            "position_errors": [],
            "expected": {},
            "actual": {},
            "portfolio_hash": "",
            "registry_hash": "",
            "accounting_event_hash": "",
            "required_action": "BLOCK_AUTONOMOUS_CYCLE",
        }

    ready = all(prerequisite_checks.values()) and evaluation["valid"]

    return {
        "stage": "V392.13A",
        "state": (
            "PAPER_PORTFOLIO_RECONCILIATION_READY"
            if ready
            else "PAPER_PORTFOLIO_RECONCILIATION_BLOCKED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "prerequisite_checks": prerequisite_checks,
        "evaluation": evaluation,
        "portfolio_reconciled": ready,
        "autonomous_cycle_orchestrator_allowed": ready,
        "fail_closed_enabled": True,
        "cash_reconciliation_enabled": True,
        "position_reconciliation_enabled": True,
        "pnl_reconciliation_enabled": True,
        "duplicate_fill_detection_enabled": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V392_14A_AUTONOMOUS_PAPER_CYCLE_ORCHESTRATOR",
    }
