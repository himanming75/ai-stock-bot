from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {
    "PAUSE",
    "RESUME",
    "APPROVE_RETRY",
    "REJECT_RETRY",
    "CLEAR_STALE_LOCK",
    "END_SESSION",
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


def request_id(action: str, observed_at: str) -> str:
    raw = f"{action}|{observed_at}".encode("utf-8")
    return "operator-request-" + hashlib.sha256(raw).hexdigest()[:20]


def first_state(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value:
            return str(value)
    return "NOT_AVAILABLE"


def run_operator_control_center(
    *,
    certification_result_path: Path,
    orchestrator_result_path: Path,
    recovery_result_path: Path,
    retry_result_path: Path,
    approval_result_path: Path,
    guard_result_path: Path,
    runner_result_path: Path,
    policy_path: Path,
    control_lock_path: Path,
    control_request_path: Path,
    control_ledger_path: Path,
    unified_dashboard_path: Path,
    result_path: Path,
    action: str = "",
    note: str = "",
    clear_control_lock: bool = False,
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
    for name, path in {
        "certification": certification_result_path,
        "orchestrator": orchestrator_result_path,
        "recovery": recovery_result_path,
        "retry": retry_result_path,
        "approval": approval_result_path,
        "guard": guard_result_path,
        "runner": runner_result_path,
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
            "code": "OPERATOR_CONTROL_POLICY_NOT_FOUND",
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
        ("AUTOMATIC_CONTROL_EXECUTION_MUST_BE_DISABLED",
         not bool(policy.get("automatic_control_execution_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "operator control safety policy failed",
            })

    existing_lock = load_json(control_lock_path)
    normalized_action = action.strip().upper()
    state = "OPERATOR_CONTROL_CENTER_READY"
    status = "PASS"
    current_request_id = str(existing_lock.get("request_id", ""))
    request_written = False
    lock_written = False

    if any(item.get("blocking") for item in issues):
        state = "OPERATOR_CONTROL_CENTER_SAFE_MODE"
        status = "BLOCKED"
    elif clear_control_lock:
        write_json(control_lock_path, {
            "active": False,
            "request_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "OPERATOR_CONTROL_LOCK_CLEARED"
    elif normalized_action:
        if normalized_action not in ALLOWED_ACTIONS:
            issues.append({
                "code": "OPERATOR_ACTION_NOT_ALLOWED",
                "blocking": True,
                "detail": normalized_action,
            })
            state = "OPERATOR_CONTROL_CENTER_SAFE_MODE"
            status = "BLOCKED"
        elif bool(existing_lock.get("active", False)):
            issues.append({
                "code": "DUPLICATE_OPERATOR_REQUEST_BLOCKED",
                "blocking": True,
                "detail": current_request_id,
            })
            state = "OPERATOR_CONTROL_CENTER_SAFE_MODE"
            status = "BLOCKED"
        else:
            current_request_id = request_id(
                normalized_action,
                observed_iso,
            )
            request = {
                "stage": "V83.71",
                "state": "OPERATOR_ACTION_PENDING",
                "request_id": current_request_id,
                "action": normalized_action,
                "note": note,
                "automatic_control_execution_enabled": False,
                "operator_confirmation_required": True,
                "paper_only": True,
                "created_at": observed_iso,
            }
            write_json(control_request_path, request)
            write_json(control_lock_path, {
                "active": True,
                "request_id": current_request_id,
                "action": normalized_action,
                "created_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(control_ledger_path, {
                **request,
                "event": "OPERATOR_ACTION_REQUESTED",
            })
            request_written = True
            lock_written = True
            state = "OPERATOR_ACTION_PENDING"

    certification_state = first_state(
        values["certification"],
        "state",
        "paper_cycle_certification_state",
    )
    full_cycle_state = first_state(
        values["orchestrator"],
        "state",
        "full_cycle_state",
    )
    recovery_state = first_state(
        values["recovery"],
        "state",
        "restart_recovery_state",
    )
    retry_state = first_state(
        values["retry"],
        "state",
        "trigger_retry_policy_state",
    )
    approval_state = first_state(
        values["approval"],
        "state",
        "retry_approval_state",
    )
    guard_state = first_state(
        values["guard"],
        "state",
        "reentry_execution_guard_state",
    )
    runner_state = first_state(
        values["runner"],
        "state",
        "supervised_reentry_runner_state",
    )

    requires_attention = any(
        token in value
        for value in (
            full_cycle_state,
            recovery_state,
            retry_state,
            approval_state,
            guard_state,
            runner_state,
        )
        for token in (
            "RECOVERY_REQUIRED",
            "MANUAL_INTERVENTION",
            "SAFE_MODE",
            "BUDGET_EXHAUSTED",
            "EXPIRED",
        )
    )

    dashboard = {
        "stage": "V83.72",
        "state": state,
        "status": status,
        "operator_control_center_state": state,
        "certification_state": certification_state,
        "full_cycle_state": full_cycle_state,
        "recovery_state": recovery_state,
        "retry_state": retry_state,
        "approval_state": approval_state,
        "guard_state": guard_state,
        "runner_state": runner_state,
        "requires_operator_attention": requires_attention,
        "requested_action": normalized_action,
        "request_id": current_request_id,
        "request_written": request_written,
        "control_lock_written": lock_written,
        "allowed_actions": sorted(ALLOWED_ACTIONS),
        "operator_supervision_required": True,
        "automatic_control_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(unified_dashboard_path, dashboard)

    append_jsonl(control_ledger_path, {
        "stage": "V83.70",
        "event": "UNIFIED_OPERATOR_DASHBOARD_OBSERVED",
        "state": state,
        "status": status,
        "requires_operator_attention": requires_attention,
        "observed_at": observed_iso,
        "paper_only": True,
    })

    result = {
        **dashboard,
        "stage_range": "V83.69-V83.72",
        "implementation_type": (
            "OPERATOR_CONTROL_CENTER_AND_UNIFIED_DASHBOARD"
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
            "V83_73_PAPER_AUTONOMOUS_MODE"
            if status == "PASS"
            else "V83_69_TO_V83_72_RECOVER"
        ),
        "validation_mode": "LOCAL_OPERATOR_CONTROL_PLANNING_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
