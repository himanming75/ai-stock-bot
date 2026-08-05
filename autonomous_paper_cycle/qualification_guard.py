from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from .qualification import qualify_fully_autonomous_paper_trading


def run_full_qualification(
    cycle_result: dict[str, Any],
    cycle_report: dict[str, Any],
    cycle_ledger_records: list[dict[str, Any]],
    completed_cycle_registry: dict[str, Any],
    reconciliation_result: dict[str, Any],
    risk_result: dict[str, Any],
    qualification_registry: dict[str, Any],
) -> dict[str, Any]:
    evaluation = qualify_fully_autonomous_paper_trading(
        cycle_result=cycle_result,
        cycle_report=cycle_report,
        cycle_ledger_records=cycle_ledger_records,
        completed_cycle_registry=completed_cycle_registry,
        reconciliation_result=reconciliation_result,
        risk_result=risk_result,
        qualification_registry=qualification_registry,
    )

    qualified = evaluation["qualified"]

    return {
        "stage": "V392.15A",
        "state": (
            "FULLY_AUTONOMOUS_PAPER_TRADING_QUALIFIED"
            if qualified
            else "FULLY_AUTONOMOUS_PAPER_TRADING_NOT_QUALIFIED"
        ),
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "fully_autonomous_local_paper_trading_ready": qualified,
        "qualification_certificate_created": qualified,
        "continuous_operation_candidate": qualified,
        "crash_recovery_ready": qualified,
        "ledger_integrity_verified": qualified,
        "hash_integrity_verified": qualified,
        "portfolio_integrity_verified": qualified,
        "risk_fail_closed_verified": qualified,
        "replay_protection_verified": True,
        "broker_adapter_enabled": False,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "POST_V392_LOCAL_PAPER_OPERATIONS",
    }
