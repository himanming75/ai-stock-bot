
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {
    "START_PAPER_SESSION": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_21_TO_V82_24_PAPER_SESSION_MANAGER.ps1",
        "-StartSession",
    ],
    "REFRESH_SCHEDULER_HEARTBEAT": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_25_TO_V82_28_PAPER_SCHEDULER.ps1",
        "-WriteHeartbeat",
    ],
    "AUTHORIZE_SCHEDULER_TICK": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_25_TO_V82_28_PAPER_SCHEDULER.ps1",
        "-AuthorizeTick",
    ],
    "EXECUTE_INTRADAY_LOOP": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_29_TO_V82_32_INTRADAY_LOOP.ps1",
        "-ExecuteLoop",
    ],
    "RESUME_INTRADAY_LOOP": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_29_TO_V82_32_INTRADAY_LOOP.ps1",
        "-ResumeLoop",
    ],
    "COMPLETE_SCHEDULER_TICK": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_25_TO_V82_28_PAPER_SCHEDULER.ps1",
        "-CompleteTick",
    ],
    "END_PAPER_SESSION": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_21_TO_V82_24_PAPER_SESSION_MANAGER.ps1",
        "-EndSession",
    ],
    "REFRESH_END_OF_DAY_STATE": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_33_TO_V82_36_END_OF_DAY.ps1",
    ],
    "CERTIFY_TRADING_DAY": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_33_TO_V82_36_END_OF_DAY.ps1",
        "-CertifyDay",
    ],
    "PREPARE_NEXT_TRADING_DAY": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_33_TO_V82_36_END_OF_DAY.ps1",
        "-PrepareNextDay",
    ],
    "EXECUTE_MULTI_DAY_ROLLOVER": [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "RUN_V82_37_TO_V82_40_MULTI_DAY_RUNTIME.ps1",
        "-ExecuteRollover",
    ],
}


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


def relative_command(command: list[str], repository_root: Path) -> list[str]:
    result = list(command)
    if "-File" in result:
        index = result.index("-File") + 1
        result[index] = str((repository_root / result[index]).resolve())
    return result


def complete_orchestrator_lock(
    *,
    action_lock_path: Path,
    action_id: str,
    action: str,
    completed_at: str,
) -> None:
    write_json(action_lock_path, {
        "active": False,
        "action_id": action_id,
        "action": action,
        "completed_at": completed_at,
        "paper_only": True,
    })


def run_local_action_dispatcher(
    *,
    repository_root: Path,
    action_plan_path: Path,
    action_lock_path: Path,
    policy_path: Path,
    dispatch_lock_path: Path,
    dispatch_ledger_path: Path,
    execution_report_path: Path,
    recovery_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_action: bool = False,
    dry_run: bool = False,
    clear_dispatch_lock: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    try:
        plan = load_json(action_plan_path)
    except Exception as exc:
        plan = {}
        issues.append({
            "code": "INVALID_ORCHESTRATOR_ACTION_PLAN",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        orchestrator_lock = load_json(action_lock_path)
    except Exception as exc:
        orchestrator_lock = {}
        issues.append({
            "code": "INVALID_ORCHESTRATOR_ACTION_LOCK",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_DISPATCHER_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "DISPATCHER_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    safety_checks = (
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
            "CONTINUOUS_LOOP_MUST_BE_DISABLED",
            not bool(policy.get("continuous_loop_enabled", True)),
        ),
        (
            "BROKER_COMMANDS_MUST_BE_DISABLED",
            not bool(policy.get("broker_command_execution_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "dispatcher safety policy failed",
            })

    action = str(plan.get("action", ""))
    action_id = str(plan.get("action_id", ""))
    plan_authorized = bool(action_id) and bool(action)
    orchestrator_action_active = (
        bool(orchestrator_lock.get("active", False))
        and str(orchestrator_lock.get("action_id", "")) == action_id
    )

    if action not in ALLOWED_ACTIONS and plan_authorized:
        issues.append({
            "code": "ACTION_NOT_IN_LOCAL_ALLOWLIST",
            "blocking": True,
            "detail": action,
        })

    if execute_action and not plan_authorized:
        issues.append({
            "code": "AUTHORIZED_ACTION_PLAN_REQUIRED",
            "blocking": True,
            "detail": str(action_plan_path),
        })

    if execute_action and not orchestrator_action_active:
        issues.append({
            "code": "ACTIVE_ORCHESTRATOR_LOCK_REQUIRED",
            "blocking": True,
            "detail": action_id,
        })

    dispatch_lock = load_json(dispatch_lock_path)
    active_dispatch = bool(dispatch_lock.get("active", False))
    duplicate_dispatch = execute_action and active_dispatch
    if duplicate_dispatch:
        issues.append({
            "code": "DUPLICATE_LOCAL_DISPATCH_BLOCKED",
            "blocking": True,
            "detail": str(dispatch_lock.get("action_id", "")),
        })

    command = (
        relative_command(ALLOWED_ACTIONS[action], repository_root)
        if action in ALLOWED_ACTIONS
        else []
    )
    timeout_seconds = int(policy.get("timeout_seconds", 120))

    blocking = any(item.get("blocking") for item in issues)
    dispatch_started = False
    dispatch_completed = False
    dispatch_succeeded = False
    dispatch_lock_written = False
    dispatch_ledger_written = False
    execution_report_written = False
    recovery_written = False
    orchestrator_lock_completed = False
    return_code: int | None = None
    stdout = ""
    stderr = ""

    if blocking:
        state, status = "LOCAL_ACTION_DISPATCHER_SAFE_MODE", "BLOCKED"

    elif clear_dispatch_lock:
        write_json(dispatch_lock_path, {
            "active": False,
            "action_id": "",
            "cleared_at": now_iso,
            "paper_only": True,
        })
        dispatch_lock_written = True
        state, status = "LOCAL_DISPATCH_LOCK_CLEARED", "PASS"

    elif not execute_action:
        if plan_authorized and orchestrator_action_active:
            state, status = "LOCAL_ACTION_READY", "PASS"
        else:
            state, status = "WAIT_AUTHORIZED_ORCHESTRATOR_ACTION", "PASS"

    elif dry_run:
        report = {
            "stage": "V83.06-V83.07",
            "action_id": action_id,
            "action": action,
            "command": command,
            "dry_run": True,
            "executed": False,
            "return_code": None,
            "stdout": "",
            "stderr": "",
            "observed_at": now_iso,
            "paper_only": True,
        }
        write_json(execution_report_path, report)
        execution_report_written = True
        append_jsonl(dispatch_ledger_path, {
            **report,
            "event": "LOCAL_ACTION_DRY_RUN",
        })
        dispatch_ledger_written = True
        state, status = "LOCAL_ACTION_DRY_RUN_COMPLETE", "PASS"

    else:
        write_json(dispatch_lock_path, {
            "stage": "V83.05",
            "active": True,
            "action_id": action_id,
            "action": action,
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
            dispatch_succeeded = return_code == 0

            report = {
                "stage": "V83.06-V83.07",
                "action_id": action_id,
                "action": action,
                "command": command,
                "dry_run": False,
                "executed": True,
                "return_code": return_code,
                "stdout": stdout[-12000:],
                "stderr": stderr[-12000:],
                "started_at": now_iso,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "paper_only": True,
            }
            write_json(execution_report_path, report)
            execution_report_written = True

            append_jsonl(dispatch_ledger_path, {
                **report,
                "event": (
                    "LOCAL_ACTION_EXECUTION_SUCCEEDED"
                    if dispatch_succeeded
                    else "LOCAL_ACTION_EXECUTION_FAILED"
                ),
            })
            dispatch_ledger_written = True

            if dispatch_succeeded:
                completed_at = datetime.now(timezone.utc).isoformat()
                complete_orchestrator_lock(
                    action_lock_path=action_lock_path,
                    action_id=action_id,
                    action=action,
                    completed_at=completed_at,
                )
                orchestrator_lock_completed = True
                write_json(dispatch_lock_path, {
                    "active": False,
                    "action_id": action_id,
                    "action": action,
                    "completed_at": completed_at,
                    "paper_only": True,
                })
                state, status = "LOCAL_ACTION_DISPATCH_COMPLETE", "PASS"
            else:
                write_json(recovery_path, {
                    "stage": "V83.07",
                    "recovery_required": True,
                    "action_id": action_id,
                    "action": action,
                    "return_code": return_code,
                    "reason": "LOCAL_COMMAND_RETURNED_NONZERO",
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                    "paper_only": True,
                })
                recovery_written = True
                state, status = "LOCAL_ACTION_DISPATCH_FAILED", "BLOCKED"

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            write_json(recovery_path, {
                "stage": "V83.07",
                "recovery_required": True,
                "action_id": action_id,
                "action": action,
                "return_code": None,
                "reason": "LOCAL_COMMAND_TIMEOUT",
                "timeout_seconds": timeout_seconds,
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "paper_only": True,
            })
            recovery_written = True
            state, status = "LOCAL_ACTION_DISPATCH_TIMEOUT", "BLOCKED"

    if not recovery_written:
        write_json(recovery_path, {
            "stage": "V83.07",
            "recovery_required": state in {
                "LOCAL_ACTION_DISPATCH_FAILED",
                "LOCAL_ACTION_DISPATCH_TIMEOUT",
                "LOCAL_ACTION_DISPATCHER_SAFE_MODE",
            },
            "action_id": action_id,
            "action": action,
            "observed_at": now_iso,
            "paper_only": True,
        })
        recovery_written = True

    dashboard = {
        "stage": "V83.08",
        "dispatcher_state": state,
        "action_id": action_id,
        "action": action,
        "plan_authorized": plan_authorized,
        "orchestrator_action_active": orchestrator_action_active,
        "dispatch_started": dispatch_started,
        "dispatch_completed": dispatch_completed,
        "dispatch_succeeded": dispatch_succeeded,
        "dry_run": dry_run,
        "return_code": return_code,
        "orchestrator_lock_completed": orchestrator_lock_completed,
        "broker_command_execution_enabled": False,
        "continuous_loop_enabled": False,
        "paper_only": True,
        "read_only": False if dispatch_started else True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.05-V83.08",
        "implementation_type": "LOCAL_ACTION_DISPATCHER_FOUNDATION",
        "status": status,
        "state": state,
        "action_id": action_id,
        "action": action,
        "command": command,
        "plan_authorized": plan_authorized,
        "orchestrator_action_active": orchestrator_action_active,
        "execute_action_requested": execute_action,
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
        "execution_report_written": execution_report_written,
        "dispatch_lock_written": dispatch_lock_written,
        "dispatch_ledger_written": dispatch_ledger_written,
        "recovery_snapshot_written": recovery_written,
        "dashboard_state_written": True,
        "orchestrator_lock_completed": orchestrator_lock_completed,
        "command_execution_enabled": True,
        "broker_command_execution_enabled": False,
        "automatic_action_execution_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_install_enabled": False,
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
            "V83_09_CONTROLLED_AUTOMATION_CYCLE"
            if state in {
                "LOCAL_ACTION_READY",
                "LOCAL_ACTION_DRY_RUN_COMPLETE",
                "LOCAL_ACTION_DISPATCH_COMPLETE",
                "WAIT_AUTHORIZED_ORCHESTRATOR_ACTION",
            }
            else "V83_05_TO_V83_08_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_ALLOWLISTED_ACTION_DISPATCH_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
