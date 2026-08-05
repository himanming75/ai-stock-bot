from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .p5_checkpoint import read_checkpoint, write_checkpoint
from .p5_fault_matrix import run_fault_matrix
from .p5_metrics import QualificationMetrics
from .p5_models import QualificationPolicy


def run_long_run_qualification(
    *,
    policy: QualificationPolicy,
    cycle_runner: Callable[[int], dict[str, Any]],
    checkpoint_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    policy.validate()
    metrics = QualificationMetrics()

    prior = read_checkpoint(checkpoint_path)
    start_cycle = 1
    if prior and prior.get("state") == "INTERRUPTED":
        start_cycle = int(prior.get("next_cycle", 1))
        metrics.restart_recoveries_passed += 1

    for cycle_number in range(start_cycle, policy.required_cycles + 1):
        result = cycle_runner(cycle_number)
        if result.get("status") == "PASS":
            metrics.record_success()
        else:
            metrics.record_failure()

        write_checkpoint(checkpoint_path, {
            "stage": "P5",
            "state": "RUNNING",
            "last_completed_cycle": cycle_number,
            "next_cycle": cycle_number + 1,
            "metrics": metrics.as_dict(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        if metrics.failed_cycles > policy.maximum_failed_cycles:
            break
        if (
            metrics.maximum_observed_consecutive_failures
            > policy.maximum_consecutive_failures
        ):
            break

    faults = run_fault_matrix()
    metrics.duplicate_cycles_blocked = int(
        faults["checks"]["duplicate_cycle_blocked"]
    )
    metrics.kill_switch_tests_passed = int(
        faults["checks"]["kill_switch_blocks"]
    )
    metrics.reconciliation_tests_passed = int(
        faults["checks"]["position_drift_blocks"]
        and faults["checks"]["account_drift_blocks"]
    )
    metrics.market_close_tests_passed = int(
        faults["checks"]["market_closed_blocks"]
    )
    metrics.next_day_resume_tests_passed = int(
        faults["checks"]["next_day_resume_supported"]
    )

    qualification_checks = {
        "required_cycles_completed": (
            metrics.successful_cycles == policy.required_cycles
        ),
        "failed_cycles_within_limit": (
            metrics.failed_cycles <= policy.maximum_failed_cycles
        ),
        "consecutive_failures_within_limit": (
            metrics.maximum_observed_consecutive_failures
            <= policy.maximum_consecutive_failures
        ),
        "fault_matrix_passed": faults["passed"],
        "restart_recovery": (
            not policy.require_restart_recovery
            or faults["checks"]["restart_checkpoint_restored"]
        ),
        "duplicate_protection": (
            not policy.require_duplicate_protection
            or faults["checks"]["duplicate_cycle_blocked"]
        ),
        "kill_switch_test": (
            not policy.require_kill_switch_test
            or faults["checks"]["kill_switch_blocks"]
        ),
        "reconciliation_test": (
            not policy.require_reconciliation_test
            or (
                faults["checks"]["position_drift_blocks"]
                and faults["checks"]["account_drift_blocks"]
            )
        ),
        "market_close_test": (
            not policy.require_market_close_test
            or faults["checks"]["market_closed_blocks"]
        ),
        "next_day_resume_test": (
            not policy.require_next_day_resume_test
            or faults["checks"]["next_day_resume_supported"]
        ),
    }

    qualified = all(qualification_checks.values())
    result = {
        "stage": "P5",
        "state": (
            "PAPER_LONG_RUN_OFFLINE_QUALIFIED"
            if qualified
            else "PAPER_LONG_RUN_QUALIFICATION_BLOCKED"
        ),
        "status": "PASS" if qualified else "FAIL",
        "qualified": qualified,
        "qualification_mode": "OFFLINE",
        "metrics": metrics.as_dict(),
        "fault_matrix": faults,
        "qualification_checks": qualification_checks,
        "actual_paper_long_run_qualified": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "paper_complete": False,
        "live_complete": False,
        "next_fixed_stage": "L1_LIVE_SAFETY_BOUNDARY_AFTER_ACTUAL_PAPER_QUALIFICATION",
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        __import__("json").dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_checkpoint(checkpoint_path, {
        "stage": "P5",
        "state": "COMPLETE" if qualified else "BLOCKED",
        "next_cycle": policy.required_cycles + 1,
        "metrics": metrics.as_dict(),
    })
    return result
