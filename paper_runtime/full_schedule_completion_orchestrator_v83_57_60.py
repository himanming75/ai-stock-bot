from __future__ import annotations

import hashlib
import json
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


def cycle_id(observed_at: str, trigger_id: str) -> str:
    raw = f"{observed_at}|{trigger_id}".encode("utf-8")
    return "paper-cycle-" + hashlib.sha256(raw).hexdigest()[:20]


def derive_state(values: dict[str, dict[str, Any]]) -> str:
    completion = values["retry_completion"]
    runner = values["runner"]
    guard = values["guard"]
    approval = values["approval"]
    retry = values["retry"]
    chain = values["chain"]
    dispatcher = values["dispatcher"]
    schedule = values["schedule"]

    completion_state = str(completion.get("state", ""))
    if completion_state == "RETRY_CYCLE_COMPLETED":
        return "FULL_CYCLE_COMPLETED"
    if completion_state == "RETRY_CYCLE_BUDGET_EXHAUSTED":
        return "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED"
    if completion_state == "RETRY_CYCLE_FAILED_RETRY_AVAILABLE":
        return "FULL_CYCLE_RETRY_AVAILABLE"

    runner_state = str(runner.get("state", ""))
    if runner_state == "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED":
        return "FULL_CYCLE_RECOVERY_REQUIRED"
    if runner_state == "SUPERVISED_REENTRY_RUNNER_COMPLETED":
        return "FULL_CYCLE_COMPLETION_PENDING"

    guard_state = str(guard.get("state", ""))
    if guard_state in {
        "REENTRY_EXECUTION_DRY_RUN_READY",
        "REENTRY_EXECUTION_SUPERVISED_READY",
        "REENTRY_EXECUTION_GUARD_ACTIVE",
    }:
        return "FULL_CYCLE_REENTRY_READY"

    approval_state = str(approval.get("state", ""))
    if approval_state == "SUPERVISED_REENTRY_READY":
        return "FULL_CYCLE_APPROVAL_READY"

    retry_state = str(retry.get("state", ""))
    if retry_state == "TRIGGER_RETRY_READY":
        return "FULL_CYCLE_RETRY_READY"
    if retry_state == "TRIGGER_RETRY_PLANNED":
        return "FULL_CYCLE_RETRY_PLANNED"
    if retry_state == "TRIGGER_RETRY_BUDGET_EXHAUSTED":
        return "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED"

    chain_state = str(chain.get("state", ""))
    if chain_state == "TRIGGER_CHAIN_DISPATCH_RUNNING":
        return "FULL_CYCLE_DISPATCH_RUNNING"
    if chain_state == "TRIGGER_CHAIN_DISPATCH_READY":
        return "FULL_CYCLE_DISPATCH_READY"
    if chain_state == "TRIGGER_CHAIN_RECOVERY_REQUIRED":
        return "FULL_CYCLE_RECOVERY_REQUIRED"
    if chain_state == "TRIGGER_CHAIN_COMPLETED":
        return "FULL_CYCLE_COMPLETION_PENDING"

    dispatcher_state = str(dispatcher.get("state", ""))
    if dispatcher_state == "LOCAL_TRIGGER_DISPATCH_COMPLETED":
        return "FULL_CYCLE_COMPLETION_PENDING"
    if dispatcher_state == "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED":
        return "FULL_CYCLE_RECOVERY_REQUIRED"

    schedule_state = str(schedule.get("state", ""))
    if schedule_state in {
        "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER",
        "LOCAL_TRIGGER_DISPATCH_DRY_RUN_READY",
        "",
    }:
        return "FULL_CYCLE_WAIT_SCHEDULE"

    return "FULL_CYCLE_OBSERVING"


def run_full_schedule_completion_orchestrator(
    *,
    schedule_result_path: Path,
    dispatcher_result_path: Path,
    chain_result_path: Path,
    retry_result_path: Path,
    approval_result_path: Path,
    guard_result_path: Path,
    runner_result_path: Path,
    retry_completion_result_path: Path,
    policy_path: Path,
    cycle_lock_path: Path,
    ledger_path: Path,
    certificate_path: Path,
    dashboard_path: Path,
    result_path: Path,
    start_cycle: bool = False,
    finalize_cycle: bool = False,
    clear_cycle_lock: bool = False,
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
        "schedule": schedule_result_path,
        "dispatcher": dispatcher_result_path,
        "chain": chain_result_path,
        "retry": retry_result_path,
        "approval": approval_result_path,
        "guard": guard_result_path,
        "runner": runner_result_path,
        "retry_completion": retry_completion_result_path,
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
            "code": "ORCHESTRATOR_POLICY_NOT_FOUND",
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
        ("AUTOMATIC_STAGE_EXECUTION_MUST_BE_DISABLED",
         not bool(policy.get("automatic_stage_execution_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "orchestrator safety policy failed",
            })

    current_lock = load_json(cycle_lock_path)
    trigger_id = str(
        values["retry_completion"].get(
            "trigger_id",
            values["chain"].get(
                "trigger_id",
                values["dispatcher"].get("trigger_id", ""),
            ),
        )
    )
    current_cycle_id = str(current_lock.get("cycle_id", ""))
    state = derive_state(values)
    status = "PASS"
    cycle_started = False
    cycle_finalized = False
    certificate_written = False

    if any(item.get("blocking") for item in issues):
        state = "FULL_CYCLE_SAFE_MODE"
        status = "BLOCKED"
    elif clear_cycle_lock:
        write_json(cycle_lock_path, {
            "active": False,
            "cycle_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "FULL_CYCLE_LOCK_CLEARED"
    elif start_cycle:
        if bool(current_lock.get("active", False)):
            issues.append({
                "code": "DUPLICATE_FULL_CYCLE_BLOCKED",
                "blocking": True,
                "detail": current_cycle_id,
            })
            state = "FULL_CYCLE_SAFE_MODE"
            status = "BLOCKED"
        else:
            current_cycle_id = cycle_id(observed_iso, trigger_id)
            write_json(cycle_lock_path, {
                "active": True,
                "cycle_id": current_cycle_id,
                "trigger_id": trigger_id,
                "started_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(ledger_path, {
                "stage": "V83.57",
                "event": "FULL_CYCLE_STARTED",
                "cycle_id": current_cycle_id,
                "trigger_id": trigger_id,
                "state": state,
                "started_at": observed_iso,
                "paper_only": True,
            })
            cycle_started = True
    elif finalize_cycle:
        if not bool(current_lock.get("active", False)):
            issues.append({
                "code": "FULL_CYCLE_LOCK_NOT_ACTIVE",
                "blocking": True,
                "detail": "",
            })
            state = "FULL_CYCLE_SAFE_MODE"
            status = "BLOCKED"
        elif state not in {
            "FULL_CYCLE_COMPLETED",
            "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED",
        }:
            issues.append({
                "code": "FULL_CYCLE_NOT_FINALIZABLE",
                "blocking": True,
                "detail": state,
            })
            state = "FULL_CYCLE_SAFE_MODE"
            status = "BLOCKED"
        else:
            completed_at = datetime.now(timezone.utc).isoformat()
            current_cycle_id = str(current_lock.get("cycle_id", ""))
            certificate = {
                "stage": "V83.60",
                "certificate_type": "FULL_SCHEDULE_TO_COMPLETION_CERTIFICATE",
                "cycle_id": current_cycle_id,
                "trigger_id": trigger_id,
                "state": state,
                "manual_intervention_required": (
                    state == "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED"
                ),
                "paper_only": True,
                "actual_paper_orders_submitted": 0,
                "live_orders_submitted": 0,
                "issued_at": completed_at,
            }
            write_json(certificate_path, certificate)
            write_json(cycle_lock_path, {
                "active": False,
                "cycle_id": current_cycle_id,
                "completed_at": completed_at,
                "paper_only": True,
            })
            append_jsonl(ledger_path, {
                **certificate,
                "event": "FULL_CYCLE_FINALIZED",
            })
            cycle_finalized = True
            certificate_written = True

    append_jsonl(ledger_path, {
        "stage": "V83.59",
        "event": "FULL_CYCLE_OBSERVED",
        "cycle_id": current_cycle_id,
        "state": state,
        "status": status,
        "observed_at": observed_iso,
        "paper_only": True,
    })

    dashboard = {
        "stage": "V83.60",
        "state": state,
        "status": status,
        "full_cycle_state": state,
        "cycle_id": current_cycle_id,
        "trigger_id": trigger_id,
        "start_cycle_requested": start_cycle,
        "finalize_cycle_requested": finalize_cycle,
        "cycle_started": cycle_started,
        "cycle_finalized": cycle_finalized,
        "certificate_written": certificate_written,
        "manual_intervention_required": (
            state == "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED"
        ),
        "operator_supervision_required": True,
        "automatic_stage_execution_enabled": False,
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
        "stage_range": "V83.57-V83.60",
        "implementation_type": (
            "FULL_SCHEDULE_TO_COMPLETION_ORCHESTRATOR"
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
            "V83_61_CRASH_RECOVERY_AND_RESTART_CONTINUATION"
            if status == "PASS"
            else "V83_57_TO_V83_60_RECOVER"
        ),
        "validation_mode": "LOCAL_ORCHESTRATION_STATE_ONLY",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
