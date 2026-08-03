from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_STAGES = (
    "SCHEDULE_EVALUATION",
    "TRIGGER_DISPATCH",
    "SUPERVISED_RUNNER",
    "RETRY_EVALUATION",
    "CYCLE_COMPLETION",
)


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


def autonomous_cycle_id(observed_at: str) -> str:
    raw = f"paper-autonomous|{observed_at}".encode("utf-8")
    return "paper-auto-cycle-" + hashlib.sha256(raw).hexdigest()[:20]


def derive_plan(
    control: dict[str, Any],
    certification: dict[str, Any],
    orchestrator: dict[str, Any],
) -> tuple[str, list[str]]:
    control_state = str(control.get("state", ""))
    certification_state = str(certification.get("state", ""))
    full_cycle_state = str(orchestrator.get("state", ""))

    if control.get("requires_operator_attention") is True:
        return "PAPER_AUTONOMOUS_OPERATOR_ATTENTION_REQUIRED", []

    if control_state not in {
        "OPERATOR_CONTROL_CENTER_READY",
        "OPERATOR_CONTROL_LOCK_CLEARED",
        "",
    }:
        return "PAPER_AUTONOMOUS_CONTROL_BLOCKED", []

    if certification_state not in {
        "PAPER_CYCLE_CERTIFICATION_READY",
        "END_TO_END_PAPER_AUTOMATION_CERTIFIED",
        "",
    }:
        return "PAPER_AUTONOMOUS_CERTIFICATION_REQUIRED", []

    if full_cycle_state in {
        "FULL_CYCLE_RECOVERY_REQUIRED",
        "FULL_CYCLE_MANUAL_INTERVENTION_REQUIRED",
    }:
        return "PAPER_AUTONOMOUS_RECOVERY_REQUIRED", []

    if full_cycle_state in {
        "FULL_CYCLE_DISPATCH_RUNNING",
        "FULL_CYCLE_REENTRY_READY",
        "FULL_CYCLE_COMPLETION_PENDING",
    }:
        return "PAPER_AUTONOMOUS_EXISTING_CYCLE_ACTIVE", []

    return "PAPER_AUTONOMOUS_CYCLE_READY", list(ALLOWED_STAGES)


def run_paper_autonomous_mode(
    *,
    control_center_result_path: Path,
    certification_result_path: Path,
    orchestrator_result_path: Path,
    recovery_result_path: Path,
    policy_path: Path,
    autonomous_lock_path: Path,
    autonomous_plan_path: Path,
    autonomous_ledger_path: Path,
    dashboard_path: Path,
    result_path: Path,
    authorize_autonomous_cycle: bool = False,
    complete_cycle: bool = False,
    clear_autonomous_lock: bool = False,
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
        "control": control_center_result_path,
        "certification": certification_result_path,
        "orchestrator": orchestrator_result_path,
        "recovery": recovery_result_path,
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
            "code": "PAPER_AUTONOMOUS_POLICY_NOT_FOUND",
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
        ("CONTINUOUS_LOOP_MUST_BE_DISABLED",
         not bool(policy.get("continuous_loop_enabled", True))),
        ("WINDOWS_TASK_MUST_BE_DISABLED",
         not bool(policy.get("windows_task_enabled", True))),
    ):
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "paper autonomous safety policy failed",
            })

    lock = load_json(autonomous_lock_path)
    state, planned_stages = derive_plan(
        values["control"],
        values["certification"],
        values["orchestrator"],
    )
    status = "PASS"
    cycle_id = str(lock.get("cycle_id", ""))
    plan_written = False
    lock_written = False
    cycle_completed = False

    if any(item.get("blocking") for item in issues):
        state = "PAPER_AUTONOMOUS_SAFE_MODE"
        status = "BLOCKED"

    elif clear_autonomous_lock:
        write_json(autonomous_lock_path, {
            "active": False,
            "cycle_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        state = "PAPER_AUTONOMOUS_LOCK_CLEARED"

    elif complete_cycle:
        if not bool(lock.get("active", False)):
            issues.append({
                "code": "PAPER_AUTONOMOUS_LOCK_NOT_ACTIVE",
                "blocking": True,
                "detail": "",
            })
            state = "PAPER_AUTONOMOUS_SAFE_MODE"
            status = "BLOCKED"
        else:
            cycle_id = str(lock.get("cycle_id", ""))
            write_json(autonomous_lock_path, {
                "active": False,
                "cycle_id": cycle_id,
                "completed_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(autonomous_ledger_path, {
                "stage": "V83.75",
                "event": "PAPER_AUTONOMOUS_CYCLE_COMPLETED",
                "cycle_id": cycle_id,
                "completed_at": observed_iso,
                "paper_only": True,
            })
            state = "PAPER_AUTONOMOUS_CYCLE_COMPLETED"
            cycle_completed = True

    elif authorize_autonomous_cycle:
        if state != "PAPER_AUTONOMOUS_CYCLE_READY":
            issues.append({
                "code": "PAPER_AUTONOMOUS_NOT_READY",
                "blocking": True,
                "detail": state,
            })
            state = "PAPER_AUTONOMOUS_SAFE_MODE"
            status = "BLOCKED"
        elif bool(lock.get("active", False)):
            issues.append({
                "code": "DUPLICATE_PAPER_AUTONOMOUS_CYCLE_BLOCKED",
                "blocking": True,
                "detail": cycle_id,
            })
            state = "PAPER_AUTONOMOUS_SAFE_MODE"
            status = "BLOCKED"
        else:
            cycle_id = autonomous_cycle_id(observed_iso)
            plan = {
                "stage": "V83.74",
                "state": "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
                "cycle_id": cycle_id,
                "planned_stages": planned_stages,
                "single_cycle_only": True,
                "continuous_loop_enabled": False,
                "windows_task_enabled": False,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "automatic_broker_execution_enabled": False,
                "operator_override_available": True,
                "paper_only": True,
                "created_at": observed_iso,
            }
            write_json(autonomous_plan_path, plan)
            write_json(autonomous_lock_path, {
                "active": True,
                "cycle_id": cycle_id,
                "created_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(autonomous_ledger_path, {
                **plan,
                "event": "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
            })
            plan_written = True
            lock_written = True
            state = "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED"

    elif bool(lock.get("active", False)):
        state = "PAPER_AUTONOMOUS_CYCLE_ACTIVE"

    dashboard = {
        "stage": "V83.76",
        "state": state,
        "status": status,
        "paper_autonomous_mode_state": state,
        "cycle_id": cycle_id,
        "authorize_autonomous_cycle_requested": authorize_autonomous_cycle,
        "complete_cycle_requested": complete_cycle,
        "planned_stages": planned_stages,
        "plan_written": plan_written,
        "lock_written": lock_written,
        "cycle_completed": cycle_completed,
        "single_cycle_only": True,
        "operator_supervision_available": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
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

    append_jsonl(autonomous_ledger_path, {
        "stage": "V83.73",
        "event": "PAPER_AUTONOMOUS_MODE_EVALUATED",
        "state": state,
        "status": status,
        "cycle_id": cycle_id,
        "observed_at": observed_iso,
        "paper_only": True,
    })

    result = {
        **dashboard,
        "stage_range": "V83.73-V83.76",
        "implementation_type": "PAPER_AUTONOMOUS_MODE_INTEGRATION",
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
            "V83_77_MULTI_DAY_PAPER_VALIDATION"
            if status == "PASS"
            else "V83_73_TO_V83_76_RECOVER"
        ),
        "validation_mode": "LOCAL_SINGLE_CYCLE_AUTONOMOUS_PLANNING",
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
