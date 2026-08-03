from __future__ import annotations
from typing import Any

def evaluate_close_gates(
    account: dict[str, Any],
    risk: dict[str, Any],
    simulation: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "account_reconciliation_passed": (
            account.get("state") == "PAPER_ACCOUNT_RECONCILIATION_PASS"
        ),
        "account_integrity_passed": (
            account.get("integrity", {}).get("passed") is True
        ),
        "risk_center_approved": risk.get("risk_approved") is True,
        "simulation_completed": (
            simulation.get("state")
            == "PAPER_EXECUTION_SIMULATION_COMPLETED"
        ),
        "actual_orders_zero": (
            simulation.get("actual_orders_submitted") == 0
            and account.get("actual_orders_submitted") == 0
        ),
        "paper_only": (
            simulation.get("paper_only") is True
            and account.get("paper_only") is True
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "passed": not failed,
        "checks": checks,
        "failed": failed,
    }
