from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def recovery_id(trigger_id: str, observed_at: str) -> str:
    value = f"{trigger_id}|{observed_at}".encode("utf-8")
    return "trigger-recovery-" + hashlib.sha256(value).hexdigest()[:20]


def contract_valid(plan: dict[str, Any]) -> bool:
    return (
        plan.get("action") == ALLOWED_ACTION
        and Path(str(plan.get("target_script", ""))).name
        == ALLOWED_TARGET_SCRIPT
        and tuple(plan.get("target_arguments", []))
        == ALLOWED_TARGET_ARGUMENTS
        and bool(plan.get("paper_only", False))
    )


def derive_chain_state(
    *,
    trigger_plan: dict[str, Any],
    trigger_lock: dict[str, Any],
    dispatch_lock: dict[str, Any],
    dispatcher_result: dict[str, Any],
    completion_result: dict[str, Any],
    recovery_snapshot: dict[str, Any],
) -> str:
    if completion_result.get("state") == "LOCAL_TRIGGER_COMPLETED_BY_DISPATCHER":
        return "TRIGGER_CHAIN_COMPLETED"
    if dispatcher_result.get("state") == "LOCAL_TRIGGER_DISPATCH_COMPLETED":
        return "TRIGGER_CHAIN_COMPLETED"
    if recovery_snapshot.get("state") == "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED":
        return "TRIGGER_CHAIN_RECOVERY_REQUIRED"
    if dispatcher_result.get("state") == "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED":
        return "TRIGGER_CHAIN_RECOVERY_REQUIRED"
    if bool(dispatch_lock.get("active", False)):
        return "TRIGGER_CHAIN_DISPATCH_RUNNING"
    if trigger_plan and bool(trigger_lock.get("active", False)):
        return "TRIGGER_CHAIN_DISPATCH_READY"
    if trigger_plan:
        return "TRIGGER_CHAIN_TRIGGER_PENDING"
    return "TRIGGER_CHAIN_WAIT_TRIGGER"


def run_trigger_recovery_dispatch_chain(
    *,
    trigger_plan_path: Path,
    trigger_lock_path: Path,
    dispatch_lock_path: Path,
    dispatcher_result_path: Path,
    recovery_snapshot_path: Path,
    completion_result_path: Path,
    recovery_lock_path: Path,
    chain_ledger_path: Path,
    dashboard_path: Path,
    result_path: Path,
    policy_path: Path,
    recover_trigger: bool = False,
    clear_recovery_lock: bool = False,
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
        "trigger_plan": trigger_plan_path,
        "trigger_lock": trigger_lock_path,
        "dispatch_lock": dispatch_lock_path,
        "dispatcher_result": dispatcher_result_path,
        "recovery_snapshot": recovery_snapshot_path,
        "completion_result": completion_result_path,
        "recovery_lock": recovery_lock_path,
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
            "code": "CHAIN_POLICY_NOT_FOUND",
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
        ("WINDOWS_TASK_INSTALL_MUST_BE_DISABLED",
         not bool(policy.get("windows_task_install_enabled", True))),
        ("CONTINUOUS_LOOP_MUST_BE_DISABLED",
         not bool(policy.get("continuous_loop_enabled", True))),
        ("AUTO_DISPATCH_MUST_BE_DISABLED",
         not bool(policy.get("automatic_dispatch_enabled", True))),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "trigger recovery chain safety policy failed",
            })

    if clear_recovery_lock:
        write_json(recovery_lock_path, {
            "active": False,
            "recovery_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })

    trigger_plan = inputs["trigger_plan"]
    trigger_lock = inputs["trigger_lock"]
    dispatch_lock = inputs["dispatch_lock"]
    dispatcher_result = inputs["dispatcher_result"]
    recovery_snapshot = inputs["recovery_snapshot"]
    completion_result = inputs["completion_result"]
    current_recovery_lock = (
        {} if clear_recovery_lock else inputs["recovery_lock"]
    )

    chain_state_before = derive_chain_state(
        trigger_plan=trigger_plan,
        trigger_lock=trigger_lock,
        dispatch_lock=dispatch_lock,
        dispatcher_result=dispatcher_result,
        completion_result=completion_result,
        recovery_snapshot=recovery_snapshot,
    )

    recovery_requested = recover_trigger
    recovery_completed = False
    recovery_lock_written = False
    trigger_lock_restored = False
    current_recovery_id = str(current_recovery_lock.get("recovery_id", ""))

    if recover_trigger:
        snapshot_trigger_id = str(recovery_snapshot.get("trigger_id", ""))
        plan_trigger_id = str(trigger_plan.get("trigger_id", ""))
        duplicate_recovery = bool(current_recovery_lock.get("active", False))

        if duplicate_recovery:
            issues.append({
                "code": "DUPLICATE_TRIGGER_RECOVERY_BLOCKED",
                "blocking": True,
                "detail": current_recovery_id,
            })
        if not recovery_snapshot:
            issues.append({
                "code": "RECOVERY_SNAPSHOT_NOT_FOUND",
                "blocking": True,
                "detail": str(recovery_snapshot_path),
            })
        if recovery_snapshot and (
            recovery_snapshot.get("state")
            != "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED"
        ):
            issues.append({
                "code": "RECOVERY_SNAPSHOT_STATE_INVALID",
                "blocking": True,
                "detail": str(recovery_snapshot.get("state", "")),
            })
        if not trigger_plan:
            issues.append({
                "code": "RECOVERY_TRIGGER_PLAN_NOT_FOUND",
                "blocking": True,
                "detail": str(trigger_plan_path),
            })
        elif not contract_valid(trigger_plan):
            issues.append({
                "code": "RECOVERY_TRIGGER_CONTRACT_INVALID",
                "blocking": True,
                "detail": plan_trigger_id,
            })
        if snapshot_trigger_id != plan_trigger_id:
            issues.append({
                "code": "RECOVERY_TRIGGER_ID_MISMATCH",
                "blocking": True,
                "detail": (
                    f"snapshot={snapshot_trigger_id};plan={plan_trigger_id}"
                ),
            })
        if bool(dispatch_lock.get("active", False)):
            issues.append({
                "code": "ACTIVE_DISPATCH_BLOCKS_RECOVERY",
                "blocking": True,
                "detail": str(dispatch_lock.get("dispatch_id", "")),
            })

        if not any(item.get("blocking") for item in issues):
            current_recovery_id = recovery_id(plan_trigger_id, observed_iso)
            write_json(recovery_lock_path, {
                "active": True,
                "recovery_id": current_recovery_id,
                "trigger_id": plan_trigger_id,
                "started_at": observed_iso,
                "paper_only": True,
            })
            recovery_lock_written = True

            write_json(trigger_lock_path, {
                "active": True,
                "trigger_id": plan_trigger_id,
                "trading_date": trigger_plan.get("trading_date", ""),
                "restored_at": observed_iso,
                "restored_by": "V83.33_TRIGGER_RECOVERY_MANAGER",
                "recovery_id": current_recovery_id,
                "paper_only": True,
            })
            trigger_lock_restored = True

            completed_iso = datetime.now(timezone.utc).isoformat()
            write_json(recovery_lock_path, {
                "active": False,
                "recovery_id": current_recovery_id,
                "trigger_id": plan_trigger_id,
                "completed_at": completed_iso,
                "paper_only": True,
            })
            append_jsonl(chain_ledger_path, {
                "stage": "V83.33",
                "event": "TRIGGER_RECOVERY_COMPLETED",
                "recovery_id": current_recovery_id,
                "trigger_id": plan_trigger_id,
                "completed_at": completed_iso,
                "paper_only": True,
            })
            recovery_completed = True

    blocking = any(item.get("blocking") for item in issues)
    if blocking:
        status = "BLOCKED"
        state = "TRIGGER_CHAIN_SAFE_MODE"
    else:
        status = "PASS"
        refreshed_trigger_lock = (
            load_json(trigger_lock_path)
            if trigger_lock_restored
            else trigger_lock
        )
        state = derive_chain_state(
            trigger_plan=trigger_plan,
            trigger_lock=refreshed_trigger_lock,
            dispatch_lock=dispatch_lock,
            dispatcher_result=dispatcher_result,
            completion_result=completion_result,
            recovery_snapshot=(
                {} if recovery_completed else recovery_snapshot
            ),
        )
        if clear_recovery_lock and not recover_trigger:
            state = "TRIGGER_RECOVERY_LOCK_CLEARED"

    append_jsonl(chain_ledger_path, {
        "stage": "V83.35",
        "event": "TRIGGER_DISPATCH_CHAIN_OBSERVED",
        "state": state,
        "status": status,
        "chain_state_before": chain_state_before,
        "recovery_requested": recovery_requested,
        "recovery_completed": recovery_completed,
        "trigger_id": str(trigger_plan.get("trigger_id", "")),
        "dispatch_id": str(dispatch_lock.get("dispatch_id", "")),
        "observed_at": observed_iso,
        "paper_only": True,
    })

    dashboard = {
        "stage": "V83.36",
        "trigger_dispatch_chain_state": state,
        "state": state,
        "status": status,
        "chain_state_before": chain_state_before,
        "trigger_pending": state == "TRIGGER_CHAIN_TRIGGER_PENDING",
        "dispatch_ready": state == "TRIGGER_CHAIN_DISPATCH_READY",
        "dispatch_running": state == "TRIGGER_CHAIN_DISPATCH_RUNNING",
        "completed": state == "TRIGGER_CHAIN_COMPLETED",
        "recovery_required": state == "TRIGGER_CHAIN_RECOVERY_REQUIRED",
        "waiting_trigger": state == "TRIGGER_CHAIN_WAIT_TRIGGER",
        "recovery_requested": recovery_requested,
        "recovery_completed": recovery_completed,
        "recovery_id": current_recovery_id,
        "trigger_id": str(trigger_plan.get("trigger_id", "")),
        "dispatch_id": str(dispatch_lock.get("dispatch_id", "")),
        "operator_supervision_required": True,
        "automatic_dispatch_enabled": False,
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
        "stage_range": "V83.33-V83.36",
        "implementation_type": (
            "TRIGGER_RECOVERY_AND_DISPATCH_CHAIN_INTEGRATION"
        ),
        "recovery_lock_written": recovery_lock_written,
        "trigger_lock_restored": trigger_lock_restored,
        "chain_ledger_written": True,
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
            "V83_37_TRIGGER_CHAIN_POLICY_AND_RETRY_BUDGET"
            if status == "PASS"
            else "V83_33_TO_V83_36_RECOVER"
        ),
        "validation_mode": "LOCAL_TRIGGER_CHAIN_STATE_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
