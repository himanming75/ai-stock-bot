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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


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


def retry_plan_id(trigger_id: str, attempt: int, observed_at: str) -> str:
    raw = f"{trigger_id}|{attempt}|{observed_at}".encode("utf-8")
    return "retry-plan-" + hashlib.sha256(raw).hexdigest()[:20]


def failure_is_retryable(
    recovery_snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[bool, str]:
    if not recovery_snapshot:
        return False, "NO_RECOVERY_SNAPSHOT"

    if recovery_snapshot.get("state") != (
        "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED"
    ):
        return False, "RECOVERY_STATE_NOT_RETRYABLE"

    timed_out = bool(recovery_snapshot.get("timed_out", False))
    return_code = recovery_snapshot.get("return_code")
    retryable_codes = {
        int(value) for value in policy.get("retryable_return_codes", [])
    }

    if timed_out and bool(policy.get("retry_timeout_failures", True)):
        return True, "TIMEOUT_RETRYABLE"

    if return_code is not None and int(return_code) in retryable_codes:
        return True, "RETURN_CODE_RETRYABLE"

    return False, "FAILURE_NOT_RETRYABLE"


def count_retry_attempts(
    rows: list[dict[str, Any]],
    trigger_id: str,
) -> int:
    return sum(
        1
        for row in rows
        if row.get("event") == "TRIGGER_RETRY_PLANNED"
        and str(row.get("trigger_id", "")) == trigger_id
    )


def run_trigger_chain_retry_policy(
    *,
    chain_result_path: Path,
    trigger_plan_path: Path,
    trigger_lock_path: Path,
    recovery_snapshot_path: Path,
    policy_path: Path,
    retry_lock_path: Path,
    retry_ledger_path: Path,
    retry_plan_path: Path,
    dashboard_path: Path,
    result_path: Path,
    plan_retry: bool = False,
    complete_retry: bool = False,
    clear_retry_lock: bool = False,
    observed_at_override: str = "",
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
    inputs: dict[str, dict[str, Any]] = {}
    for name, path in {
        "chain_result": chain_result_path,
        "trigger_plan": trigger_plan_path,
        "trigger_lock": trigger_lock_path,
        "recovery_snapshot": recovery_snapshot_path,
        "policy": policy_path,
    }.items():
        try:
            inputs[name] = load_json(path)
        except Exception as exc:
            inputs[name] = {}
            issues.append({
                "code": f"INVALID_{name.upper()}",
                "blocking": True,
                "detail": str(exc),
            })

    policy = inputs["policy"]
    if not policy:
        issues.append({
            "code": "RETRY_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    safety_checks = (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED",
         not bool(policy.get("broker_write_enabled", True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED",
         not bool(policy.get("order_submission_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED",
         not bool(policy.get("live_trading_enabled", True))),
        ("EXTERNAL_NETWORK_MUST_BE_DISABLED",
         not bool(policy.get("external_network_enabled", True))),
        ("AUTOMATIC_RETRY_EXECUTION_MUST_BE_DISABLED",
         not bool(policy.get("automatic_retry_execution_enabled", True))),
        ("CONTINUOUS_LOOP_MUST_BE_DISABLED",
         not bool(policy.get("continuous_loop_enabled", True))),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "retry safety policy failed",
            })

    chain_result = inputs["chain_result"]
    trigger_plan = inputs["trigger_plan"]
    trigger_lock = inputs["trigger_lock"]
    recovery_snapshot = inputs["recovery_snapshot"]

    retry_lock = load_json(retry_lock_path)
    history = load_jsonl(retry_ledger_path)
    trigger_id = str(
        recovery_snapshot.get(
            "trigger_id",
            trigger_plan.get("trigger_id", ""),
        )
    )
    attempts_used = count_retry_attempts(history, trigger_id)
    max_attempts = int(policy.get("max_retry_attempts", 3) or 3)
    base_backoff_seconds = int(
        policy.get("base_backoff_seconds", 60) or 60
    )
    max_backoff_seconds = int(
        policy.get("max_backoff_seconds", 900) or 900
    )
    retryable, retry_reason = failure_is_retryable(
        recovery_snapshot,
        policy,
    )
    attempts_remaining = max(max_attempts - attempts_used, 0)
    budget_exhausted = attempts_used >= max_attempts
    duplicate_retry = plan_retry and bool(retry_lock.get("active", False))

    if duplicate_retry:
        issues.append({
            "code": "DUPLICATE_RETRY_PLAN_BLOCKED",
            "blocking": True,
            "detail": str(retry_lock.get("retry_plan_id", "")),
        })

    if plan_retry:
        if not trigger_id:
            issues.append({
                "code": "RETRY_TRIGGER_ID_MISSING",
                "blocking": True,
                "detail": "",
            })
        if not retryable:
            issues.append({
                "code": "FAILURE_NOT_RETRYABLE",
                "blocking": True,
                "detail": retry_reason,
            })
        if budget_exhausted:
            issues.append({
                "code": "RETRY_BUDGET_EXHAUSTED",
                "blocking": True,
                "detail": f"{attempts_used}/{max_attempts}",
            })
        if trigger_plan and (
            str(trigger_plan.get("trigger_id", "")) != trigger_id
        ):
            issues.append({
                "code": "RETRY_TRIGGER_PLAN_ID_MISMATCH",
                "blocking": True,
                "detail": trigger_id,
            })

    state = "TRIGGER_RETRY_POLICY_IDLE"
    status = "PASS"
    retry_plan_written = False
    retry_lock_written = False
    retry_completed = False
    current_retry_plan_id = str(retry_lock.get("retry_plan_id", ""))
    next_retry_at = ""

    if clear_retry_lock:
        write_json(retry_lock_path, {
            "active": False,
            "retry_plan_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "TRIGGER_RETRY_LOCK_CLEARED"

    elif any(item.get("blocking") for item in issues):
        state = (
            "TRIGGER_RETRY_BUDGET_EXHAUSTED"
            if any(
                item.get("code") == "RETRY_BUDGET_EXHAUSTED"
                for item in issues
            )
            else "TRIGGER_RETRY_SAFE_MODE"
        )
        status = "BLOCKED"

    elif complete_retry:
        if bool(retry_lock.get("active", False)):
            completed_iso = datetime.now(timezone.utc).isoformat()
            current_retry_plan_id = str(
                retry_lock.get("retry_plan_id", "")
            )
            write_json(retry_lock_path, {
                "active": False,
                "retry_plan_id": current_retry_plan_id,
                "trigger_id": str(retry_lock.get("trigger_id", "")),
                "completed_at": completed_iso,
                "paper_only": True,
            })
            append_jsonl(retry_ledger_path, {
                "stage": "V83.39",
                "event": "TRIGGER_RETRY_COMPLETED",
                "retry_plan_id": current_retry_plan_id,
                "trigger_id": str(retry_lock.get("trigger_id", "")),
                "completed_at": completed_iso,
                "paper_only": True,
            })
            retry_lock_written = True
            retry_completed = True
            state = "TRIGGER_RETRY_COMPLETED"
        else:
            state = "NO_ACTIVE_TRIGGER_RETRY"

    elif plan_retry:
        attempt_number = attempts_used + 1
        backoff_seconds = min(
            base_backoff_seconds * (2 ** (attempt_number - 1)),
            max_backoff_seconds,
        )
        next_retry_at = (
            observed_at + timedelta(seconds=backoff_seconds)
        ).isoformat()
        current_retry_plan_id = retry_plan_id(
            trigger_id,
            attempt_number,
            observed_iso,
        )
        plan = {
            "stage": "V83.38",
            "retry_plan_id": current_retry_plan_id,
            "trigger_id": trigger_id,
            "attempt_number": attempt_number,
            "max_retry_attempts": max_attempts,
            "backoff_seconds": backoff_seconds,
            "next_retry_at": next_retry_at,
            "action": "RESTORE_TRIGGER_FOR_SUPERVISED_RETRY",
            "automatic_retry_execution_enabled": False,
            "operator_approval_required": True,
            "paper_only": True,
            "created_at": observed_iso,
        }
        write_json(retry_plan_path, plan)
        write_json(retry_lock_path, {
            "active": True,
            "retry_plan_id": current_retry_plan_id,
            "trigger_id": trigger_id,
            "attempt_number": attempt_number,
            "created_at": observed_iso,
            "paper_only": True,
        })
        append_jsonl(retry_ledger_path, {
            **plan,
            "event": "TRIGGER_RETRY_PLANNED",
        })
        retry_plan_written = True
        retry_lock_written = True
        attempts_used = attempt_number
        attempts_remaining = max(max_attempts - attempts_used, 0)
        state = "TRIGGER_RETRY_PLANNED"

    else:
        chain_state = str(chain_result.get("state", ""))
        if bool(retry_lock.get("active", False)):
            state = "TRIGGER_RETRY_IN_PROGRESS"
        elif budget_exhausted:
            state = "TRIGGER_RETRY_BUDGET_EXHAUSTED"
        elif retryable:
            state = "TRIGGER_RETRY_READY"
        elif chain_state == "TRIGGER_CHAIN_RECOVERY_REQUIRED":
            state = "TRIGGER_RETRY_NOT_ELIGIBLE"
        else:
            state = "TRIGGER_RETRY_WAIT_FAILURE"

    dashboard = {
        "stage": "V83.40",
        "trigger_retry_policy_state": state,
        "state": state,
        "status": status,
        "trigger_id": trigger_id,
        "retry_plan_id": current_retry_plan_id,
        "retryable": retryable,
        "retry_reason": retry_reason,
        "attempts_used": attempts_used,
        "attempts_remaining": attempts_remaining,
        "max_retry_attempts": max_attempts,
        "budget_exhausted": attempts_used >= max_attempts,
        "next_retry_at": next_retry_at,
        "retry_plan_written": retry_plan_written,
        "retry_completed": retry_completed,
        "operator_supervision_required": True,
        "automatic_retry_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.37-V83.40",
        "implementation_type": (
            "TRIGGER_CHAIN_POLICY_AND_RETRY_BUDGET"
        ),
        "plan_retry_requested": plan_retry,
        "complete_retry_requested": complete_retry,
        "clear_retry_lock_requested": clear_retry_lock,
        "duplicate_retry": duplicate_retry,
        "retry_lock_written": retry_lock_written,
        "dashboard_state_written": True,
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
            "V83_41_RETRY_APPROVAL_AND_SUPERVISED_REENTRY"
            if status == "PASS"
            else "V83_37_TO_V83_40_RECOVER"
        ),
        "validation_mode": "LOCAL_RETRY_POLICY_PLANNING_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
