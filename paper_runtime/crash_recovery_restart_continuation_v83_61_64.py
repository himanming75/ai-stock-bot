from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def recovery_id(cycle_id: str, observed_at: str) -> str:
    raw = f"{cycle_id}|{observed_at}".encode("utf-8")
    return "restart-recovery-" + hashlib.sha256(raw).hexdigest()[:20]


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def run_crash_recovery_restart_continuation(
    *,
    orchestrator_result_path: Path,
    cycle_lock_path: Path,
    dispatcher_lock_path: Path,
    runner_lock_path: Path,
    retry_lock_path: Path,
    approval_lock_path: Path,
    policy_path: Path,
    recovery_lock_path: Path,
    recovery_plan_path: Path,
    recovery_snapshot_path: Path,
    recovery_ledger_path: Path,
    dashboard_path: Path,
    result_path: Path,
    analyze: bool = False,
    apply_recovery: bool = False,
    clear_stale_locks: bool = False,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    observed_iso = observed.isoformat()

    issues: list[dict[str, Any]] = []
    values: dict[str, dict[str, Any]] = {}
    paths = {
        "orchestrator_result": orchestrator_result_path,
        "cycle_lock": cycle_lock_path,
        "dispatcher_lock": dispatcher_lock_path,
        "runner_lock": runner_lock_path,
        "retry_lock": retry_lock_path,
        "approval_lock": approval_lock_path,
        "policy": policy_path,
        "recovery_lock": recovery_lock_path,
    }
    for name, path in paths.items():
        try:
            values[name] = load_json(path)
        except Exception as exc:
            values[name] = {}
            issues.append({
                "code": f"INVALID_{name.upper()}",
                "blocking": True,
                "detail": str(exc),
            })

    policy = values["policy"]
    if not policy:
        issues.append({
            "code": "CRASH_RECOVERY_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    for code, passed in (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED",
         not bool(policy.get("broker_write_enabled", True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED",
         not bool(policy.get("order_submission_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED",
         not bool(policy.get("live_trading_enabled", True))),
        ("EXTERNAL_NETWORK_MUST_BE_DISABLED",
         not bool(policy.get("external_network_enabled", True))),
        ("AUTOMATIC_RESUME_MUST_BE_DISABLED",
         not bool(policy.get("automatic_resume_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "crash recovery safety policy failed",
            })

    stale_after_seconds = int(
        policy.get("stale_lock_after_seconds", 1800) or 1800
    )
    orchestrator = values["orchestrator_result"]
    cycle_lock = values["cycle_lock"]
    dispatcher_lock = values["dispatcher_lock"]
    runner_lock = values["runner_lock"]
    retry_lock = values["retry_lock"]
    approval_lock = values["approval_lock"]
    existing_recovery_lock = values["recovery_lock"]

    state = "RESTART_RECOVERY_IDLE"
    status = "PASS"
    decision = "NO_ACTION"
    stale_locks: list[str] = []
    active_locks: list[str] = []
    recovery_plan_written = False
    recovery_applied = False
    recovery_snapshot_written = False
    current_recovery_id = str(
        existing_recovery_lock.get("recovery_id", "")
    )

    lock_map = {
        "cycle_lock": cycle_lock,
        "dispatcher_lock": dispatcher_lock,
        "runner_lock": runner_lock,
        "retry_lock": retry_lock,
        "approval_lock": approval_lock,
    }
    for name, lock in lock_map.items():
        if not bool(lock.get("active", False)):
            continue
        active_locks.append(name)
        timestamp = str(
            lock.get(
                "started_at",
                lock.get(
                    "created_at",
                    lock.get("approved_at", ""),
                ),
            )
        )
        parsed = parse_time(timestamp)
        if parsed and observed - parsed > timedelta(
            seconds=stale_after_seconds
        ):
            stale_locks.append(name)

    orchestrator_state = str(orchestrator.get("state", ""))
    cycle_active = bool(cycle_lock.get("active", False))

    if any(item.get("blocking") for item in issues):
        state = "RESTART_RECOVERY_SAFE_MODE"
        status = "BLOCKED"
    elif not analyze and not apply_recovery and not clear_stale_locks:
        state = "RESTART_RECOVERY_IDLE"
    else:
        if bool(existing_recovery_lock.get("active", False)):
            issues.append({
                "code": "DUPLICATE_RESTART_RECOVERY_BLOCKED",
                "blocking": True,
                "detail": current_recovery_id,
            })
            state = "RESTART_RECOVERY_SAFE_MODE"
            status = "BLOCKED"
        elif stale_locks:
            decision = "CLEAR_STALE_LOCKS_AND_REASSESS"
            state = "RESTART_RECOVERY_STALE_LOCKS_FOUND"
        elif cycle_active and orchestrator_state in {
            "FULL_CYCLE_DISPATCH_RUNNING",
            "FULL_CYCLE_REENTRY_READY",
            "FULL_CYCLE_COMPLETION_PENDING",
            "FULL_CYCLE_OBSERVING",
        }:
            decision = "RESUME_FROM_SAVED_STATE"
            state = "RESTART_RECOVERY_RESUME_READY"
        elif cycle_active and orchestrator_state in {
            "FULL_CYCLE_RECOVERY_REQUIRED",
            "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED",
        }:
            decision = "MANUAL_INTERVENTION_REQUIRED"
            state = "RESTART_RECOVERY_MANUAL_INTERVENTION"
        elif cycle_active:
            decision = "ABORT_INCOMPLETE_CYCLE"
            state = "RESTART_RECOVERY_ABORT_READY"
        else:
            decision = "NO_ACTIVE_CYCLE"
            state = "RESTART_RECOVERY_NO_ACTIVE_CYCLE"

        current_recovery_id = recovery_id(
            str(cycle_lock.get("cycle_id", "")),
            observed_iso,
        )
        plan = {
            "stage": "V83.62",
            "state": state,
            "recovery_id": current_recovery_id,
            "cycle_id": str(cycle_lock.get("cycle_id", "")),
            "orchestrator_state": orchestrator_state,
            "decision": decision,
            "active_locks": active_locks,
            "stale_locks": stale_locks,
            "automatic_resume_enabled": False,
            "operator_confirmation_required": True,
            "paper_only": True,
            "created_at": observed_iso,
        }
        write_json(recovery_plan_path, plan)
        recovery_plan_written = True

        if apply_recovery:
            if decision == "RESUME_FROM_SAVED_STATE":
                write_json(recovery_lock_path, {
                    "active": False,
                    "recovery_id": current_recovery_id,
                    "cycle_id": cycle_lock.get("cycle_id", ""),
                    "applied_action": "RESUME_FROM_SAVED_STATE",
                    "applied_at": observed_iso,
                    "paper_only": True,
                })
                recovery_applied = True
                state = "RESTART_RECOVERY_RESUME_APPLIED"
            elif decision == "ABORT_INCOMPLETE_CYCLE":
                write_json(cycle_lock_path, {
                    "active": False,
                    "cycle_id": cycle_lock.get("cycle_id", ""),
                    "aborted_at": observed_iso,
                    "aborted_by": "V83.63_CRASH_RECOVERY",
                    "paper_only": True,
                })
                write_json(recovery_lock_path, {
                    "active": False,
                    "recovery_id": current_recovery_id,
                    "applied_action": "ABORT_INCOMPLETE_CYCLE",
                    "applied_at": observed_iso,
                    "paper_only": True,
                })
                recovery_applied = True
                state = "RESTART_RECOVERY_ABORT_APPLIED"
            elif decision == "CLEAR_STALE_LOCKS_AND_REASSESS":
                for name in stale_locks:
                    target = paths[name]
                    write_json(target, {
                        "active": False,
                        "cleared_as_stale_at": observed_iso,
                        "cleared_by": "V83.63_CRASH_RECOVERY",
                        "paper_only": True,
                    })
                recovery_applied = True
                state = "RESTART_RECOVERY_STALE_LOCKS_CLEARED"
            else:
                issues.append({
                    "code": "RECOVERY_DECISION_NOT_APPLICABLE",
                    "blocking": True,
                    "detail": decision,
                })
                status = "BLOCKED"
                state = "RESTART_RECOVERY_SAFE_MODE"

        if clear_stale_locks and stale_locks:
            for name in stale_locks:
                target = paths[name]
                write_json(target, {
                    "active": False,
                    "cleared_as_stale_at": observed_iso,
                    "cleared_by": "V83.63_CRASH_RECOVERY",
                    "paper_only": True,
                })
            recovery_applied = True
            state = "RESTART_RECOVERY_STALE_LOCKS_CLEARED"

    snapshot = {
        "stage": "V83.63",
        "state": state,
        "decision": decision,
        "orchestrator_state": orchestrator_state,
        "active_locks": active_locks,
        "stale_locks": stale_locks,
        "captured_at": observed_iso,
        "paper_only": True,
    }
    write_json(recovery_snapshot_path, snapshot)
    recovery_snapshot_written = True

    append_jsonl(recovery_ledger_path, {
        **snapshot,
        "event": "RESTART_RECOVERY_OBSERVED",
        "recovery_id": current_recovery_id,
        "status": status,
    })

    dashboard = {
        "stage": "V83.64",
        "state": state,
        "status": status,
        "restart_recovery_state": state,
        "decision": decision,
        "recovery_id": current_recovery_id,
        "orchestrator_state": orchestrator_state,
        "active_locks": active_locks,
        "stale_locks": stale_locks,
        "recovery_plan_written": recovery_plan_written,
        "recovery_applied": recovery_applied,
        "recovery_snapshot_written": recovery_snapshot_written,
        "operator_supervision_required": True,
        "automatic_resume_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.61-V83.64",
        "implementation_type": (
            "CRASH_RECOVERY_AND_RESTART_CONTINUATION"
        ),
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V83_65_END_TO_END_PAPER_CYCLE_CERTIFICATION"
            if status == "PASS"
            else "V83_61_TO_V83_64_RECOVER"
        ),
        "validation_mode": "LOCAL_RESTART_RECOVERY_PLANNING_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
