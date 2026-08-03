from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


ALLOWED_TARGET_SCRIPT = "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1"
ALLOWED_ARGUMENTS = ("-AuthorizeRun",)


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


def execution_id(guard_id: str, observed_at: str) -> str:
    raw = f"{guard_id}|{observed_at}".encode("utf-8")
    return "reentry-execution-" + hashlib.sha256(raw).hexdigest()[:20]


def default_executor(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )


def run_supervised_reentry_runner(
    *,
    repository_root: Path,
    guard_result_path: Path,
    execution_plan_path: Path,
    execution_lock_path: Path,
    approval_lock_path: Path,
    retry_lock_path: Path,
    policy_path: Path,
    runner_lock_path: Path,
    audit_ledger_path: Path,
    recovery_snapshot_path: Path,
    completion_result_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute: bool = False,
    dry_run: bool = True,
    clear_runner_lock: bool = False,
    observed_at_override: str = "",
    executor: Callable[..., subprocess.CompletedProcess[str]] = default_executor,
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
    for name, path in {
        "guard_result": guard_result_path,
        "execution_plan": execution_plan_path,
        "execution_lock": execution_lock_path,
        "approval_lock": approval_lock_path,
        "retry_lock": retry_lock_path,
        "policy": policy_path,
    }.items():
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
            "code": "REENTRY_RUNNER_POLICY_NOT_FOUND",
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
        ("AUTOMATIC_EXECUTION_MUST_BE_DISABLED",
         not bool(policy.get("automatic_execution_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "supervised re-entry runner safety policy failed",
            })

    existing_runner_lock = load_json(runner_lock_path)
    duplicate_execution = execute and bool(
        existing_runner_lock.get("active", False)
    )
    if duplicate_execution:
        issues.append({
            "code": "DUPLICATE_REENTRY_RUNNER_BLOCKED",
            "blocking": True,
            "detail": str(existing_runner_lock.get("execution_id", "")),
        })

    state = "SUPERVISED_REENTRY_RUNNER_WAIT_PLAN"
    status = "PASS"
    execution_started = False
    execution_completed = False
    recovery_snapshot_written = False
    completion_written = False
    timed_out = False
    return_code = None
    stdout = ""
    stderr = ""
    current_execution_id = str(
        existing_runner_lock.get("execution_id", "")
    )

    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        f".\\{ALLOWED_TARGET_SCRIPT}",
        "-AuthorizeRun",
    ]

    if any(item.get("blocking") for item in issues):
        state = "SUPERVISED_REENTRY_RUNNER_SAFE_MODE"
        status = "BLOCKED"

    elif clear_runner_lock:
        write_json(runner_lock_path, {
            "active": False,
            "execution_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "SUPERVISED_REENTRY_RUNNER_LOCK_CLEARED"

    elif not execute:
        state = (
            "SUPERVISED_REENTRY_RUNNER_DRY_RUN_READY"
            if values["execution_plan"]
            else "SUPERVISED_REENTRY_RUNNER_WAIT_PLAN"
        )

    else:
        required = {
            "guard_result": values["guard_result"],
            "execution_plan": values["execution_plan"],
            "execution_lock": values["execution_lock"],
            "approval_lock": values["approval_lock"],
            "retry_lock": values["retry_lock"],
        }
        for name, value in required.items():
            if not value:
                issues.append({
                    "code": f"{name.upper()}_NOT_FOUND",
                    "blocking": True,
                    "detail": "",
                })

        guard_result = values["guard_result"]
        execution_plan = values["execution_plan"]
        execution_lock = values["execution_lock"]
        approval_lock = values["approval_lock"]
        retry_lock = values["retry_lock"]

        if guard_result and guard_result.get("state") not in {
            "REENTRY_EXECUTION_DRY_RUN_READY",
            "REENTRY_EXECUTION_SUPERVISED_READY",
        }:
            issues.append({
                "code": "REENTRY_GUARD_NOT_READY",
                "blocking": True,
                "detail": str(guard_result.get("state", "")),
            })

        if execution_plan and (
            execution_plan.get("action")
            != "RUN_SUPERVISED_REENTRY_RUNNER"
        ):
            issues.append({
                "code": "DISALLOWED_REENTRY_RUNNER_ACTION",
                "blocking": True,
                "detail": str(execution_plan.get("action", "")),
            })

        if not bool(execution_lock.get("active", False)):
            issues.append({
                "code": "REENTRY_EXECUTION_LOCK_NOT_ACTIVE",
                "blocking": True,
                "detail": str(execution_lock.get("guard_id", "")),
            })

        if not bool(approval_lock.get("active", False)):
            issues.append({
                "code": "RETRY_APPROVAL_LOCK_NOT_ACTIVE",
                "blocking": True,
                "detail": str(approval_lock.get("approval_id", "")),
            })

        if not bool(retry_lock.get("active", False)):
            issues.append({
                "code": "RETRY_LOCK_NOT_ACTIVE",
                "blocking": True,
                "detail": str(retry_lock.get("retry_plan_id", "")),
            })

        target_path = repository_root / ALLOWED_TARGET_SCRIPT
        if not target_path.exists():
            issues.append({
                "code": "AUTHORIZED_REENTRY_TARGET_NOT_FOUND",
                "blocking": True,
                "detail": str(target_path),
            })

        guard_ids = {
            str(guard_result.get("guard_id", "")),
            str(execution_plan.get("guard_id", "")),
            str(execution_lock.get("guard_id", "")),
        } - {""}
        if len(guard_ids) > 1:
            issues.append({
                "code": "REENTRY_GUARD_ID_MISMATCH",
                "blocking": True,
                "detail": sorted(guard_ids),
            })

        retry_ids = {
            str(execution_plan.get("retry_plan_id", "")),
            str(execution_lock.get("retry_plan_id", "")),
            str(approval_lock.get("retry_plan_id", "")),
            str(retry_lock.get("retry_plan_id", "")),
        } - {""}
        if len(retry_ids) > 1:
            issues.append({
                "code": "REENTRY_RETRY_PLAN_ID_MISMATCH",
                "blocking": True,
                "detail": sorted(retry_ids),
            })

        if any(item.get("blocking") for item in issues):
            state = "SUPERVISED_REENTRY_RUNNER_SAFE_MODE"
            status = "BLOCKED"
        elif dry_run:
            current_execution_id = execution_id(
                str(execution_lock.get("guard_id", "")),
                observed_iso,
            )
            append_jsonl(audit_ledger_path, {
                "stage": "V83.50",
                "event": "SUPERVISED_REENTRY_RUNNER_DRY_RUN",
                "execution_id": current_execution_id,
                "command": command,
                "observed_at": observed_iso,
                "paper_only": True,
            })
            state = "SUPERVISED_REENTRY_RUNNER_DRY_RUN_COMPLETE"
            execution_completed = True
        else:
            timeout_seconds = int(
                policy.get("timeout_seconds", 120) or 120
            )
            allowed_return_codes = [
                int(value)
                for value in policy.get("allowed_return_codes", [0])
            ]
            current_execution_id = execution_id(
                str(execution_lock.get("guard_id", "")),
                observed_iso,
            )
            write_json(runner_lock_path, {
                "active": True,
                "execution_id": current_execution_id,
                "guard_id": execution_lock.get("guard_id", ""),
                "started_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(audit_ledger_path, {
                "stage": "V83.49",
                "event": "SUPERVISED_REENTRY_RUNNER_STARTED",
                "execution_id": current_execution_id,
                "command": command,
                "started_at": observed_iso,
                "paper_only": True,
            })
            execution_started = True

            try:
                completed = executor(
                    command,
                    cwd=repository_root,
                    timeout_seconds=timeout_seconds,
                )
                return_code = int(completed.returncode)
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = str(exc.stdout or "")
                stderr = str(exc.stderr or "")
            except Exception as exc:
                stderr = str(exc)

            success = (
                not timed_out
                and return_code is not None
                and return_code in allowed_return_codes
            )

            completed_iso = datetime.now(timezone.utc).isoformat()
            if success:
                write_json(runner_lock_path, {
                    "active": False,
                    "execution_id": current_execution_id,
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                write_json(execution_lock_path, {
                    "active": False,
                    "guard_id": execution_lock.get("guard_id", ""),
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                write_json(approval_lock_path, {
                    "active": False,
                    "approval_id": approval_lock.get("approval_id", ""),
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                write_json(retry_lock_path, {
                    "active": False,
                    "retry_plan_id": retry_lock.get(
                        "retry_plan_id", ""
                    ),
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                write_json(completion_result_path, {
                    "stage": "V83.51",
                    "state": "SUPERVISED_REENTRY_RUNNER_COMPLETED",
                    "execution_id": current_execution_id,
                    "return_code": return_code,
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                append_jsonl(audit_ledger_path, {
                    "stage": "V83.51",
                    "event": "SUPERVISED_REENTRY_RUNNER_COMPLETED",
                    "execution_id": current_execution_id,
                    "return_code": return_code,
                    "completed_at": completed_iso,
                    "paper_only": True,
                })
                completion_written = True
                execution_completed = True
                state = "SUPERVISED_REENTRY_RUNNER_COMPLETED"
            else:
                issue_code = (
                    "SUPERVISED_REENTRY_RUNNER_TIMEOUT"
                    if timed_out
                    else "SUPERVISED_REENTRY_RUNNER_RETURN_CODE_FAILED"
                )
                issues.append({
                    "code": issue_code,
                    "blocking": True,
                    "detail": (
                        f"timeout={timed_out};"
                        f"return_code={return_code}"
                    ),
                })
                snapshot = {
                    "stage": "V83.51",
                    "state": "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED",
                    "execution_id": current_execution_id,
                    "timed_out": timed_out,
                    "return_code": return_code,
                    "stdout_tail": stdout[-4000:],
                    "stderr_tail": stderr[-4000:],
                    "captured_at": completed_iso,
                    "paper_only": True,
                }
                write_json(recovery_snapshot_path, snapshot)
                write_json(runner_lock_path, {
                    "active": False,
                    "execution_id": current_execution_id,
                    "failed_at": completed_iso,
                    "recovery_required": True,
                    "paper_only": True,
                })
                append_jsonl(audit_ledger_path, {
                    **snapshot,
                    "event": "SUPERVISED_REENTRY_RUNNER_FAILED",
                })
                recovery_snapshot_written = True
                state = "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED"
                status = "BLOCKED"

    dashboard = {
        "stage": "V83.52",
        "state": state,
        "status": status,
        "supervised_reentry_runner_state": state,
        "execution_id": current_execution_id,
        "execute_requested": execute,
        "dry_run": dry_run,
        "duplicate_execution": duplicate_execution,
        "execution_started": execution_started,
        "execution_completed": execution_completed,
        "completion_written": completion_written,
        "recovery_snapshot_written": recovery_snapshot_written,
        "timed_out": timed_out,
        "return_code": return_code,
        "operator_supervision_required": True,
        "automatic_execution_enabled": False,
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
        "stage_range": "V83.49-V83.52",
        "implementation_type": (
            "SUPERVISED_REENTRY_RUNNER_INTEGRATION"
        ),
        "command": command,
        "stdout": stdout,
        "stderr": stderr,
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
            "V83_53_RETRY_CYCLE_COMPLETION"
            if status == "PASS"
            else "V83_49_TO_V83_52_RECOVER"
        ),
        "validation_mode": (
            "LOCAL_SUPERVISED_REENTRY_DRY_RUN"
            if dry_run
            else "LOCAL_SUPERVISED_REENTRY_EXECUTION"
        ),
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
