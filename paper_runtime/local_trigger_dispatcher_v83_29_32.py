from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


ALLOWED_ACTION = "AUTHORIZE_SCHEDULED_SUPERVISED_RUN"
ALLOWED_TARGET_SCRIPT = "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1"
ALLOWED_TARGET_ARGUMENTS = ("-AuthorizeRun",)


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


def dispatch_id(trigger_id: str, observed_at: str) -> str:
    raw = f"{trigger_id}|{observed_at}".encode("utf-8")
    return "local-dispatch-" + hashlib.sha256(raw).hexdigest()[:20]


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


def validate_trigger_contract(
    *,
    trigger_plan: dict[str, Any],
    trigger_lock: dict[str, Any],
    policy: dict[str, Any],
    repository_root: Path,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    trigger_id_value = str(trigger_plan.get("trigger_id", ""))
    if not trigger_id_value:
        issues.append({
            "code": "TRIGGER_PLAN_ID_MISSING",
            "blocking": True,
            "detail": "trigger plan has no trigger_id",
        })

    if not bool(trigger_lock.get("active", False)):
        issues.append({
            "code": "TRIGGER_LOCK_NOT_ACTIVE",
            "blocking": True,
            "detail": str(trigger_lock.get("trigger_id", "")),
        })

    if str(trigger_lock.get("trigger_id", "")) != trigger_id_value:
        issues.append({
            "code": "TRIGGER_LOCK_ID_MISMATCH",
            "blocking": True,
            "detail": (
                f"plan={trigger_id_value};"
                f"lock={trigger_lock.get('trigger_id', '')}"
            ),
        })

    if trigger_plan.get("action") != ALLOWED_ACTION:
        issues.append({
            "code": "DISALLOWED_TRIGGER_ACTION",
            "blocking": True,
            "detail": str(trigger_plan.get("action", "")),
        })

    if Path(str(trigger_plan.get("target_script", ""))).name != ALLOWED_TARGET_SCRIPT:
        issues.append({
            "code": "DISALLOWED_TARGET_SCRIPT",
            "blocking": True,
            "detail": str(trigger_plan.get("target_script", "")),
        })

    target_arguments = tuple(trigger_plan.get("target_arguments", []))
    if target_arguments != ALLOWED_TARGET_ARGUMENTS:
        issues.append({
            "code": "DISALLOWED_TARGET_ARGUMENTS",
            "blocking": True,
            "detail": repr(target_arguments),
        })

    target_path = repository_root / ALLOWED_TARGET_SCRIPT
    if not target_path.exists():
        issues.append({
            "code": "AUTHORIZED_TARGET_NOT_FOUND",
            "blocking": True,
            "detail": str(target_path),
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
            "EXTERNAL_NETWORK_MUST_BE_DISABLED",
            not bool(policy.get("external_network_enabled", True)),
        ),
        (
            "WINDOWS_TASK_INSTALL_MUST_BE_DISABLED",
            not bool(policy.get("windows_task_install_enabled", True)),
        ),
        (
            "CONTINUOUS_LOOP_MUST_BE_DISABLED",
            not bool(policy.get("continuous_loop_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "dispatcher safety policy failed",
            })

    return issues


def run_local_trigger_dispatcher(
    *,
    repository_root: Path,
    trigger_plan_path: Path,
    trigger_lock_path: Path,
    dispatch_lock_path: Path,
    dispatch_ledger_path: Path,
    recovery_snapshot_path: Path,
    dashboard_path: Path,
    result_path: Path,
    policy_path: Path,
    trigger_completion_result_path: Path,
    dispatch: bool = False,
    dry_run: bool = True,
    clear_dispatch_lock: bool = False,
    observed_at_override: str = "",
    executor: Callable[..., subprocess.CompletedProcess[str]] = default_executor,
) -> dict[str, Any]:
    observed_at = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    observed_iso = observed_at.isoformat()

    issues: list[dict[str, Any]] = []
    try:
        trigger_plan = load_json(trigger_plan_path)
    except Exception as exc:
        trigger_plan = {}
        issues.append({
            "code": "INVALID_TRIGGER_PLAN",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        trigger_lock = load_json(trigger_lock_path)
    except Exception as exc:
        trigger_lock = {}
        issues.append({
            "code": "INVALID_TRIGGER_LOCK",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_DISPATCH_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    waiting_for_trigger = not trigger_plan and not dispatch
    if not trigger_plan and dispatch:
        issues.append({
            "code": "TRIGGER_PLAN_NOT_FOUND",
            "blocking": True,
            "detail": str(trigger_plan_path),
        })
    if not policy:
        issues.append({
            "code": "DISPATCH_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    if trigger_plan:
        issues.extend(validate_trigger_contract(
            trigger_plan=trigger_plan,
            trigger_lock=trigger_lock,
            policy=policy,
            repository_root=repository_root,
        ))

    existing_dispatch_lock = load_json(dispatch_lock_path)
    duplicate_dispatch = bool(existing_dispatch_lock.get("active", False))
    if dispatch and duplicate_dispatch:
        issues.append({
            "code": "DUPLICATE_DISPATCH_BLOCKED",
            "blocking": True,
            "detail": str(existing_dispatch_lock.get("dispatch_id", "")),
        })

    trigger_id_value = str(trigger_plan.get("trigger_id", ""))
    current_dispatch_id = str(existing_dispatch_lock.get("dispatch_id", ""))
    timeout_seconds = int(policy.get("timeout_seconds", 120) or 120)
    allowed_return_codes = [
        int(value) for value in policy.get("allowed_return_codes", [0])
    ]

    state = "LOCAL_TRIGGER_DISPATCH_READY"
    status = "PASS"
    dispatch_started = False
    dispatch_completed = False
    trigger_lock_completed = False
    recovery_snapshot_written = False
    return_code: int | None = None
    stdout = ""
    stderr = ""
    timed_out = False
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        f".\\{ALLOWED_TARGET_SCRIPT}",
        "-AuthorizeRun",
    ]

    if clear_dispatch_lock:
        write_json(dispatch_lock_path, {
            "active": False,
            "dispatch_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "LOCAL_DISPATCH_LOCK_CLEARED"

    elif waiting_for_trigger and not any(
        item.get("blocking") for item in issues
    ):
        state = "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER"

    elif any(item.get("blocking") for item in issues):
        state = "LOCAL_TRIGGER_DISPATCH_SAFE_MODE"
        status = "BLOCKED"

    elif not dispatch:
        state = (
            "LOCAL_TRIGGER_DISPATCH_DRY_RUN_READY"
            if dry_run
            else "LOCAL_TRIGGER_DISPATCH_READY"
        )

    elif dry_run:
        current_dispatch_id = dispatch_id(trigger_id_value, observed_iso)
        append_jsonl(dispatch_ledger_path, {
            "stage": "V83.30",
            "event": "LOCAL_TRIGGER_DISPATCH_DRY_RUN",
            "dispatch_id": current_dispatch_id,
            "trigger_id": trigger_id_value,
            "command": command,
            "observed_at": observed_iso,
            "paper_only": True,
        })
        state = "LOCAL_TRIGGER_DISPATCH_DRY_RUN_COMPLETE"
        dispatch_completed = True

    else:
        current_dispatch_id = dispatch_id(trigger_id_value, observed_iso)
        write_json(dispatch_lock_path, {
            "active": True,
            "dispatch_id": current_dispatch_id,
            "trigger_id": trigger_id_value,
            "started_at": observed_iso,
            "paper_only": True,
        })
        append_jsonl(dispatch_ledger_path, {
            "stage": "V83.29",
            "event": "LOCAL_TRIGGER_DISPATCH_STARTED",
            "dispatch_id": current_dispatch_id,
            "trigger_id": trigger_id_value,
            "command": command,
            "started_at": observed_iso,
            "paper_only": True,
        })
        dispatch_started = True

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

        execution_ok = (
            not timed_out
            and return_code is not None
            and return_code in allowed_return_codes
        )

        if execution_ok:
            completed_iso = datetime.now(timezone.utc).isoformat()
            append_jsonl(dispatch_ledger_path, {
                "stage": "V83.31",
                "event": "LOCAL_TRIGGER_DISPATCH_COMPLETED",
                "dispatch_id": current_dispatch_id,
                "trigger_id": trigger_id_value,
                "return_code": return_code,
                "completed_at": completed_iso,
                "paper_only": True,
            })
            write_json(dispatch_lock_path, {
                "active": False,
                "dispatch_id": current_dispatch_id,
                "trigger_id": trigger_id_value,
                "completed_at": completed_iso,
                "paper_only": True,
            })
            write_json(trigger_lock_path, {
                "active": False,
                "trigger_id": trigger_id_value,
                "completed_at": completed_iso,
                "completed_by": "V83.29-V83.32_DISPATCHER",
                "paper_only": True,
            })
            write_json(trigger_completion_result_path, {
                "stage": "V83.31",
                "state": "LOCAL_TRIGGER_COMPLETED_BY_DISPATCHER",
                "trigger_id": trigger_id_value,
                "dispatch_id": current_dispatch_id,
                "return_code": return_code,
                "completed_at": completed_iso,
                "paper_only": True,
            })
            state = "LOCAL_TRIGGER_DISPATCH_COMPLETED"
            dispatch_completed = True
            trigger_lock_completed = True
        else:
            failure_code = (
                "LOCAL_TRIGGER_DISPATCH_TIMEOUT"
                if timed_out
                else "LOCAL_TRIGGER_DISPATCH_RETURN_CODE_FAILED"
            )
            issues.append({
                "code": failure_code,
                "blocking": True,
                "detail": (
                    f"timeout={timed_out};return_code={return_code};"
                    f"allowed={allowed_return_codes}"
                ),
            })
            snapshot = {
                "stage": "V83.31",
                "state": "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED",
                "dispatch_id": current_dispatch_id,
                "trigger_id": trigger_id_value,
                "command": command,
                "timeout_seconds": timeout_seconds,
                "timed_out": timed_out,
                "return_code": return_code,
                "stdout_tail": stdout[-4000:],
                "stderr_tail": stderr[-4000:],
                "trigger_plan": trigger_plan,
                "trigger_lock": trigger_lock,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "paper_only": True,
            }
            write_json(recovery_snapshot_path, snapshot)
            append_jsonl(dispatch_ledger_path, {
                **snapshot,
                "event": "LOCAL_TRIGGER_DISPATCH_FAILED",
            })
            write_json(dispatch_lock_path, {
                "active": False,
                "dispatch_id": current_dispatch_id,
                "trigger_id": trigger_id_value,
                "failed_at": snapshot["captured_at"],
                "recovery_required": True,
                "paper_only": True,
            })
            state = "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED"
            status = "BLOCKED"
            recovery_snapshot_written = True

    dashboard = {
        "stage": "V83.32",
        "local_trigger_dispatch_state": state,
        "state": state,
        "status": status,
        "trigger_id": trigger_id_value,
        "dispatch_id": current_dispatch_id,
        "dispatch_requested": dispatch,
        "dry_run": dry_run,
        "duplicate_dispatch": duplicate_dispatch,
        "dispatch_started": dispatch_started,
        "dispatch_completed": dispatch_completed,
        "trigger_lock_completed": trigger_lock_completed,
        "timed_out": timed_out,
        "return_code": return_code,
        "timeout_seconds": timeout_seconds,
        "allowed_return_codes": allowed_return_codes,
        "operator_supervision_required": True,
        "allowed_action": ALLOWED_ACTION,
        "allowed_target_script": ALLOWED_TARGET_SCRIPT,
        "allowed_target_arguments": list(ALLOWED_TARGET_ARGUMENTS),
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "state": state,
        "stage_range": "V83.29-V83.32",
        "implementation_type": (
            "LOCAL_TRIGGER_DISPATCHER_AND_AUTO_COMPLETION_INTEGRATION"
        ),
        "command": command,
        "stdout": stdout,
        "stderr": stderr,
        "recovery_snapshot_written": recovery_snapshot_written,
        "dispatch_lock_path": str(dispatch_lock_path.resolve()),
        "dashboard_state_written": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "cancel_enabled": False,
        "replace_enabled": False,
        "position_close_enabled": False,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V83_33_DISPATCH_RECOVERY_AND_SCHEDULE_CHAIN"
            if status == "PASS"
            else "V83_29_TO_V83_32_RECOVER"
        ),
        "validation_mode": (
            "LOCAL_WHITELISTED_DISPATCH_ONLY"
            if not dry_run
            else "LOCAL_DISPATCH_DRY_RUN_ONLY"
        ),
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
