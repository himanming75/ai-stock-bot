from __future__ import annotations
from pathlib import Path
from typing import Any

from .audits import (
    crash_resume_audit,
    drift_audit,
    duplicate_cycle_audit,
    kill_switch_response_audit,
    resource_trend_audit,
)
from .continuity import (
    audit_checkpoint_continuity,
    audit_heartbeat_continuity,
)
from .fault_matrix import run_fault_matrix
from .policy import LiveLongRunPolicy


def qualify_offline(
    *,
    root: Path,
    policy: LiveLongRunPolicy,
    successful_cycles: int,
    failed_cycles: int,
) -> dict[str, Any]:
    actual_l5 = (
        root / "release/l5_live_autonomous_runtime_preparation/actual"
    )
    policy_result = policy.evaluate()
    fault_matrix = run_fault_matrix()
    heartbeat = audit_heartbeat_continuity(
        actual_l5 / "cycle_ledger.jsonl",
        maximum_gap_seconds=policy.maximum_heartbeat_gap_seconds,
    )
    checkpoint = audit_checkpoint_continuity(
        actual_l5 / "runtime_checkpoint.json"
    )
    duplicate_cycles = duplicate_cycle_audit(
        actual_l5 / "cycle_registry.json"
    )
    resources = resource_trend_audit(
        root / "release/o3_autonomous_operations/actual/"
               "resource_trends.jsonl"
    )
    drift = drift_audit(
        root / "release/l4_live_reconciliation_preparation/actual/"
               "reconciliation_ledger.jsonl"
    )
    kill_switch = kill_switch_response_audit()
    crash_resume = crash_resume_audit()

    checks = {
        "policy_valid": policy_result["valid"],
        "required_cycles_met": successful_cycles >= policy.required_cycles,
        "failed_cycles_within_limit": (
            failed_cycles <= policy.maximum_failed_cycles
        ),
        "fault_matrix_passed": fault_matrix["passed"],
        "heartbeat_continuity_passed": heartbeat["passed"],
        "checkpoint_continuity_passed": checkpoint["passed"],
        "duplicate_cycle_audit_passed": duplicate_cycles["passed"],
        "resource_trend_audit_passed": resources["passed"],
        "drift_audit_passed": drift["passed"],
        "kill_switch_response_passed": kill_switch["passed"],
        "crash_resume_passed": crash_resume["passed"],
    }
    qualified = all(checks.values())

    return {
        "stage": "L6",
        "status": "PASS" if qualified else "FAIL",
        "state": (
            "LIVE_LONG_RUN_PREPARATION_QUALIFIED"
            if qualified
            else "LIVE_LONG_RUN_PREPARATION_BLOCKED"
        ),
        "qualified": qualified,
        "successful_cycles": successful_cycles,
        "failed_cycles": failed_cycles,
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "policy": policy_result,
        "fault_matrix": fault_matrix,
        "heartbeat_continuity": heartbeat,
        "checkpoint_continuity": checkpoint,
        "duplicate_cycle_audit": duplicate_cycles,
        "resource_trend_audit": resources,
        "drift_audit": drift,
        "kill_switch_response_audit": kill_switch,
        "crash_resume_audit": crash_resume,
        "actual_live_long_run_allowed": False,
        "actual_live_long_run_qualified": False,
        "live_complete": False,
        "production_release_allowed": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "automatic_order_replay_enabled": False,
        "automatic_broker_restart_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": "L6_ACTUAL_AFTER_L5_ACTUAL_RUNTIME",
    }
