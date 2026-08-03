
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
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


def supervised_runner_command(repository_root: Path) -> list[str]:
    return [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(
            (
                repository_root
                / "RUN_V83_13_TO_V83_16_SUPERVISED_RUNNER.ps1"
            ).resolve()
        ),
        "-ExecuteRunner",
    ]


def complete_schedule_lock(
    *,
    schedule_lock_path: Path,
    authorization_id: str,
    completed_at: str,
) -> None:
    write_json(schedule_lock_path, {
        "active": False,
        "authorization_id": authorization_id,
        "completed_at": completed_at,
        "paper_only": True,
    })


def run_scheduled_dispatch(
    *,
    repository_root: Path,
    schedule_authorization_path: Path,
    schedule_lock_path: Path,
    supervised_result_path: Path,
    policy_path: Path,
    dispatch_lock_path: Path,
    dispatch_ledger_path: Path,
    execution_report_path: Path,
    recovery_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_dispatch: bool = False,
    dry_run: bool = False,
    clear_dispatch_lock: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    try:
        authorization = load_json(schedule_authorization_path)
    except Exception as exc:
        authorization = {}
        issues.append({
            "code": "INVALID_SCHEDULE_AUTHORIZATION",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        schedule_lock = load_json(schedule_lock_path)
    except Exception as exc:
        schedule_lock = {}
        issues.append({
            "code": "INVALID_SCHEDULE_LOCK",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_SCHEDULE_DISPATCH_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "SCHEDULE_DISPATCH_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    checks = (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        (
            "BROKER_WRITE_MUST_BE_DISABLED",
            not bool(policy.get("broker_write_enabled", True)),
        ),
        (
            "ORDER_SUBMISSION_MUST_BE_DISABLED",
            not bool(policy.get("order_submission_enabled", True)),
        ),
        (
            "LIVE_TRADING_MUST_BE_DISABLED",
            not bool(policy.get("live_trading_enabled", True)),
        ),
        (
            "WINDOWS_TASK_INSTALL_MUST_BE_DISABLED",
            not bool(policy.get("windows_task_install_enabled", True)),
        ),
        (
            "CONTINUOUS_LOOP_MUST_BE_DISABLED",
            not bool(policy.get("continuous_loop_enabled", True)),
        ),
        (
            "SINGLE_DISPATCH_REQUIRED",
            int(policy.get("max_dispatches_per_authorization", 0)) == 1,
        ),
    )
    for code, passed in checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "scheduled dispatch safety policy failed",
            })

    authorization_id = str(
        authorization.get("authorization_id", "")
    )
    authorization_valid = (
        bool(authorization_id)
        and bool(authorization.get("execute_supervised_runner", False))
    )
    active_schedule = (
        bool(schedule_lock.get("active", False))
        and str(schedule_lock.get("authorization_id", ""))
        == authorization_id
    )

    if execute_dispatch and not authorization_valid:
        issues.append({
            "code": "VALID_SCHEDULE_AUTHORIZATION_REQUIRED",
            "blocking": True,
            "detail": str(schedule_authorization_path),
        })

    if execute_dispatch and not active_schedule:
        issues.append({
            "code": "ACTIVE_SCHEDULE_LOCK_REQUIRED",
            "blocking": True,
            "detail": authorization_id,
        })

    dispatch_lock = load_json(dispatch_lock_path)
    active_dispatch = bool(dispatch_lock.get("active", False))
    duplicate_dispatch = execute_dispatch and active_dispatch
    if duplicate_dispatch:
        issues.append({
            "code": "DUPLICATE_SCHEDULE_DISPATCH_BLOCKED",
            "blocking": True,
            "detail": str(dispatch_lock.get("authorization_id", "")),
        })

    command = supervised_runner_command(repository_root)
    timeout_seconds = int(policy.get("timeout_seconds", 300) or 300)
    blocking = any(item.get("blocking") for item in issues)

    dispatch_started = False
    dispatch_completed = False
    dispatch_succeeded = False
    dispatch_lock_written = False
    dispatch_ledger_written = False
    execution_report_written = False
    recovery_written = False
    schedule_lock_completed = False
    supervised_result_verified = False
    return_code: int | None = None
    stdout = ""
    stderr = ""

    if blocking:
        state, status = "SCHEDULED_DISPATCH_SAFE_MODE", "BLOCKED"

    elif clear_dispatch_lock:
        write_json(dispatch_lock_path, {
            "active": False,
            "authorization_id": "",
            "cleared_at": now_iso,
            "paper_only": True,
        })
        dispatch_lock_written = True
        state, status = "SCHEDULED_DISPATCH_LOCK_CLEARED", "PASS"

    elif not execute_dispatch:
        if authorization_valid and active_schedule:
            state, status = "SCHEDULED_DISPATCH_READY", "PASS"
        else:
            state, status = "WAIT_SCHEDULED_RUN_AUTHORIZATION", "PASS"

    elif dry_run:
        report = {
            "stage": "V83.22",
            "authorization_id": authorization_id,
            "command": command,
            "dry_run": True,
            "executed": False,
            "return_code": None,
            "observed_at": now_iso,
            "paper_only": True,
        }
        write_json(execution_report_path, report)
        append_jsonl(dispatch_ledger_path, {
            **report,
            "event": "SCHEDULED_DISPATCH_DRY_RUN",
        })
        execution_report_written = True
        dispatch_ledger_written = True
        state, status = "SCHEDULED_DISPATCH_DRY_RUN_COMPLETE", "PASS"

    else:
        write_json(dispatch_lock_path, {
            "stage": "V83.21",
            "active": True,
            "authorization_id": authorization_id,
            "started_at": now_iso,
            "paper_only": True,
        })
        dispatch_lock_written = True
        dispatch_started = True

        try:
            completed = subprocess.run(
                command,
                cwd=repository_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            return_code = int(completed.returncode)
            stdout = completed.stdout
            stderr = completed.stderr
            dispatch_completed = True

            supervised_result = load_json(supervised_result_path)
            supervised_result_verified = (
                supervised_result.get("status") == "PASS"
                and supervised_result.get("state")
                == "SUPERVISED_RUNNER_COMPLETE"
                and bool(supervised_result.get("runner_completed", False))
            )
            dispatch_succeeded = (
                return_code == 0 and supervised_result_verified
            )

            completed_at = datetime.now(timezone.utc).isoformat()
            report = {
                "stage": "V83.22-V83.23",
                "authorization_id": authorization_id,
                "command": command,
                "dry_run": False,
                "executed": True,
                "return_code": return_code,
                "supervised_result_verified": (
                    supervised_result_verified
                ),
                "supervised_state": str(
                    supervised_result.get("state", "")
                ),
                "supervised_runner_id": str(
                    supervised_result.get("runner_id", "")
                ),
                "stdout": stdout[-12000:],
                "stderr": stderr[-12000:],
                "started_at": now_iso,
                "completed_at": completed_at,
                "paper_only": True,
            }
            write_json(execution_report_path, report)
            append_jsonl(dispatch_ledger_path, {
                **report,
                "event": (
                    "SCHEDULED_DISPATCH_SUCCEEDED"
                    if dispatch_succeeded
                    else "SCHEDULED_DISPATCH_FAILED"
                ),
            })
            execution_report_written = True
            dispatch_ledger_written = True

            if dispatch_succeeded:
                complete_schedule_lock(
                    schedule_lock_path=schedule_lock_path,
                    authorization_id=authorization_id,
                    completed_at=completed_at,
                )
                write_json(dispatch_lock_path, {
                    "active": False,
                    "authorization_id": authorization_id,
                    "completed_at": completed_at,
                    "paper_only": True,
                })
                schedule_lock_completed = True
                dispatch_lock_written = True
                state, status = "SCHEDULED_DISPATCH_COMPLETE", "PASS"
            else:
                write_json(recovery_path, {
                    "stage": "V83.23",
                    "recovery_required": True,
                    "authorization_id": authorization_id,
                    "return_code": return_code,
                    "supervised_result_verified": (
                        supervised_result_verified
                    ),
                    "reason": (
                        "SUPERVISED_RUNNER_RESULT_NOT_VERIFIED"
                        if return_code == 0
                        else "SUPERVISED_RUNNER_COMMAND_FAILED"
                    ),
                    "observed_at": completed_at,
                    "paper_only": True,
                })
                recovery_written = True
                state, status = "SCHEDULED_DISPATCH_FAILED", "BLOCKED"

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            write_json(recovery_path, {
                "stage": "V83.23",
                "recovery_required": True,
                "authorization_id": authorization_id,
                "reason": "SUPERVISED_RUNNER_TIMEOUT",
                "timeout_seconds": timeout_seconds,
                "observed_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "paper_only": True,
            })
            recovery_written = True
            state, status = "SCHEDULED_DISPATCH_TIMEOUT", "BLOCKED"

    if not recovery_written:
        write_json(recovery_path, {
            "stage": "V83.23",
            "recovery_required": state in {
                "SCHEDULED_DISPATCH_SAFE_MODE",
                "SCHEDULED_DISPATCH_FAILED",
                "SCHEDULED_DISPATCH_TIMEOUT",
            },
            "authorization_id": authorization_id,
            "observed_at": now_iso,
            "paper_only": True,
        })
        recovery_written = True

    dashboard = {
        "stage": "V83.24",
        "scheduled_dispatch_state": state,
        "authorization_id": authorization_id,
        "authorization_valid": authorization_valid,
        "active_schedule": active_schedule,
        "dispatch_started": dispatch_started,
        "dispatch_completed": dispatch_completed,
        "dispatch_succeeded": dispatch_succeeded,
        "supervised_result_verified": supervised_result_verified,
        "schedule_lock_completed": schedule_lock_completed,
        "return_code": return_code,
        "operator_supervision_required": True,
        "automatic_scheduling_enabled": False,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "paper_only": True,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.21-V83.24",
        "implementation_type": (
            "SCHEDULED_RUN_DISPATCH_AND_COMPLETION_INTEGRATION"
        ),
        "status": status,
        "state": state,
        "authorization_id": authorization_id,
        "authorization_valid": authorization_valid,
        "active_schedule": active_schedule,
        "execute_dispatch_requested": execute_dispatch,
        "dry_run_requested": dry_run,
        "clear_dispatch_lock_requested": clear_dispatch_lock,
        "active_dispatch": active_dispatch or (
            dispatch_started and not dispatch_succeeded
        ),
        "duplicate_dispatch": duplicate_dispatch,
        "dispatch_started": dispatch_started,
        "dispatch_completed": dispatch_completed,
        "dispatch_succeeded": dispatch_succeeded,
        "return_code": return_code,
        "supervised_result_verified": supervised_result_verified,
        "schedule_lock_completed": schedule_lock_completed,
        "dispatch_lock_written": dispatch_lock_written,
        "dispatch_ledger_written": dispatch_ledger_written,
        "execution_report_written": execution_report_written,
        "recovery_snapshot_written": recovery_written,
        "dashboard_state_written": True,
        "max_dispatches_per_authorization": 1,
        "operator_supervision_required": True,
        "automatic_scheduling_enabled": False,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "broker_command_execution_enabled": False,
        "paper_only": True,
        "read_only": not dispatch_started,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "cancel_enabled": False,
        "replace_enabled": False,
        "position_close_enabled": False,
        "live_trading_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V83_25_AUTOMATIC_SCHEDULE_EVALUATION"
            if state in {
                "WAIT_SCHEDULED_RUN_AUTHORIZATION",
                "SCHEDULED_DISPATCH_READY",
                "SCHEDULED_DISPATCH_DRY_RUN_COMPLETE",
                "SCHEDULED_DISPATCH_COMPLETE",
                "SCHEDULED_DISPATCH_LOCK_CLEARED",
            }
            else "V83_21_TO_V83_24_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SCHEDULED_SUPERVISED_DISPATCH_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
