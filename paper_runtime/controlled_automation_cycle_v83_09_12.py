
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CYCLE_STAGES = (
    "ORCHESTRATOR_EVALUATE",
    "ORCHESTRATOR_AUTHORIZE",
    "DISPATCHER_EXECUTE",
    "RUNTIME_REEVALUATE",
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


def make_cycle_id(observed_at: str, recommended_action: str) -> str:
    raw = f"{observed_at}|{recommended_action}".encode("utf-8")
    return "controlled-cycle-" + hashlib.sha256(raw).hexdigest()[:20]


def run_controlled_automation_cycle(
    *,
    orchestrator_result_path: Path,
    dispatcher_result_path: Path,
    orchestrator_action_plan_path: Path,
    orchestrator_action_lock_path: Path,
    policy_path: Path,
    cycle_lock_path: Path,
    cycle_ledger_path: Path,
    cycle_report_path: Path,
    recovery_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_cycle: bool = False,
    resume_cycle: bool = False,
    clear_cycle_lock: bool = False,
    stage_callbacks: dict[str, Callable[[], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    try:
        orchestrator = load_json(orchestrator_result_path)
    except Exception as exc:
        orchestrator = {}
        issues.append({
            "code": "INVALID_ORCHESTRATOR_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        dispatcher = load_json(dispatcher_result_path)
    except Exception as exc:
        dispatcher = {}
        issues.append({
            "code": "INVALID_DISPATCHER_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_CONTROLLED_CYCLE_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "CONTROLLED_CYCLE_POLICY_NOT_FOUND",
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
        (
            "MAX_ACTIONS_PER_CYCLE_MUST_BE_ONE",
            int(policy.get("max_actions_per_cycle", 0)) == 1,
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "controlled automation cycle safety policy failed",
            })

    recommended_action = str(
        orchestrator.get("recommended_action", "")
    )
    orchestrator_ready = (
        orchestrator.get("state") == "ORCHESTRATOR_ACTION_READY"
        and bool(orchestrator.get("action_ready", False))
    )
    wait_action = recommended_action in {
        "",
        "WAIT",
        "WAIT_NEXT_MARKET_OPEN",
    }

    existing_lock = load_json(cycle_lock_path)
    active_cycle = bool(existing_lock.get("active", False))
    duplicate_cycle = execute_cycle and active_cycle and not resume_cycle
    if duplicate_cycle:
        issues.append({
            "code": "DUPLICATE_CONTROLLED_CYCLE_BLOCKED",
            "blocking": True,
            "detail": str(existing_lock.get("cycle_id", "")),
        })

    recovery_available = (
        active_cycle
        and not bool(existing_lock.get("completed", False))
    )

    gate_reasons: list[str] = []
    if wait_action:
        gate_reasons.append("NO_EXECUTABLE_ACTION_RECOMMENDED")
    elif not orchestrator_ready and not recovery_available:
        gate_reasons.append("ORCHESTRATOR_ACTION_NOT_READY")

    callbacks = stage_callbacks or {}
    stage_results: list[dict[str, Any]] = []
    cycle_started = False
    cycle_completed = False
    cycle_recovered = False
    cycle_lock_written = False
    cycle_ledger_written = False
    cycle_report_written = False
    recovery_written = False
    last_completed_stage = str(
        existing_lock.get("last_completed_stage", "")
    )
    current_cycle_id = str(existing_lock.get("cycle_id", ""))
    authorized_action_id = ""
    dispatcher_succeeded = False
    reevaluated_state = ""

    blocking = any(item.get("blocking") for item in issues)

    if blocking:
        state, status = "CONTROLLED_AUTOMATION_CYCLE_SAFE_MODE", "BLOCKED"

    elif clear_cycle_lock:
        write_json(cycle_lock_path, {
            "active": False,
            "completed": False,
            "cycle_id": "",
            "cleared_at": now_iso,
            "paper_only": True,
        })
        cycle_lock_written = True
        state, status = "CONTROLLED_CYCLE_LOCK_CLEARED", "PASS"

    elif not execute_cycle and not resume_cycle:
        if gate_reasons:
            state, status = "CONTROLLED_CYCLE_WAIT_GATES", "PASS"
        else:
            state, status = "CONTROLLED_CYCLE_READY", "PASS"

    elif gate_reasons and not recovery_available:
        state, status = "CONTROLLED_CYCLE_WAIT_GATES", "PASS"

    elif resume_cycle and not recovery_available:
        state, status = "CONTROLLED_CYCLE_RECOVERY_NOT_AVAILABLE", "PASS"

    else:
        if resume_cycle:
            current_cycle_id = str(existing_lock.get("cycle_id", ""))
            cycle_recovered = True
        else:
            current_cycle_id = make_cycle_id(
                now_iso,
                recommended_action,
            )
            last_completed_stage = ""

        write_json(cycle_lock_path, {
            "stage": "V83.09",
            "active": True,
            "completed": False,
            "cycle_id": current_cycle_id,
            "recommended_action": recommended_action,
            "last_completed_stage": last_completed_stage,
            "started_at": str(
                existing_lock.get("started_at", now_iso)
                if resume_cycle else now_iso
            ),
            "updated_at": now_iso,
            "paper_only": True,
        })
        cycle_lock_written = True
        cycle_started = True
        started = time.perf_counter()

        try:
            resume_index = (
                CYCLE_STAGES.index(last_completed_stage) + 1
                if last_completed_stage in CYCLE_STAGES
                else 0
            )

            for stage_name in CYCLE_STAGES[resume_index:]:
                stage_started = time.perf_counter()

                if stage_name in callbacks:
                    stage_payload = callbacks[stage_name]()
                elif stage_name == "ORCHESTRATOR_EVALUATE":
                    stage_payload = {
                        "status": "PASS",
                        "recommended_action": recommended_action,
                        "action_ready": orchestrator_ready,
                    }
                elif stage_name == "ORCHESTRATOR_AUTHORIZE":
                    plan = load_json(orchestrator_action_plan_path)
                    lock = load_json(orchestrator_action_lock_path)
                    stage_payload = {
                        "status": (
                            "PASS"
                            if bool(plan.get("action_id"))
                            and bool(lock.get("active", False))
                            else "FAIL"
                        ),
                        "action_id": str(plan.get("action_id", "")),
                        "action": str(plan.get("action", "")),
                    }
                    authorized_action_id = stage_payload["action_id"]
                elif stage_name == "DISPATCHER_EXECUTE":
                    current_dispatcher = load_json(dispatcher_result_path)
                    dispatcher_succeeded = bool(
                        current_dispatcher.get(
                            "dispatch_succeeded",
                            False,
                        )
                    )
                    stage_payload = {
                        "status": (
                            "PASS" if dispatcher_succeeded else "FAIL"
                        ),
                        "dispatcher_state": str(
                            current_dispatcher.get("state", "")
                        ),
                        "return_code": current_dispatcher.get(
                            "return_code"
                        ),
                    }
                else:
                    current_orchestrator = load_json(
                        orchestrator_result_path
                    )
                    reevaluated_state = str(
                        current_orchestrator.get("state", "")
                    )
                    stage_payload = {
                        "status": "PASS",
                        "reevaluated_state": reevaluated_state,
                        "recommended_action": str(
                            current_orchestrator.get(
                                "recommended_action",
                                "",
                            )
                        ),
                    }

                stage_status = str(
                    stage_payload.get("status", "PASS")
                )
                stage_record = {
                    "stage": stage_name,
                    "status": stage_status,
                    "elapsed_ms": round(
                        (time.perf_counter() - stage_started) * 1000,
                        3,
                    ),
                    "details": {
                        key: value
                        for key, value in stage_payload.items()
                        if key != "status"
                    },
                }
                stage_results.append(stage_record)

                if stage_status != "PASS":
                    raise RuntimeError(
                        f"{stage_name} returned {stage_status}"
                    )

                last_completed_stage = stage_name
                write_json(cycle_lock_path, {
                    "stage": "V83.10",
                    "active": True,
                    "completed": False,
                    "cycle_id": current_cycle_id,
                    "recommended_action": recommended_action,
                    "last_completed_stage": last_completed_stage,
                    "started_at": str(
                        existing_lock.get("started_at", now_iso)
                        if resume_cycle else now_iso
                    ),
                    "updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "paper_only": True,
                })

            finished_at = datetime.now(timezone.utc).isoformat()
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000,
                3,
            )
            report = {
                "stage": "V83.11",
                "cycle_id": current_cycle_id,
                "recommended_action": recommended_action,
                "authorized_action_id": authorized_action_id,
                "dispatcher_succeeded": dispatcher_succeeded,
                "reevaluated_state": reevaluated_state,
                "stage_count": len(stage_results),
                "stages": stage_results,
                "recovered": cycle_recovered,
                "started_at": now_iso,
                "finished_at": finished_at,
                "elapsed_ms": elapsed_ms,
                "paper_only": True,
            }
            write_json(cycle_report_path, report)
            cycle_report_written = True

            append_jsonl(cycle_ledger_path, {
                **report,
                "event": "CONTROLLED_AUTOMATION_CYCLE_COMPLETED",
            })
            cycle_ledger_written = True

            write_json(cycle_lock_path, {
                "active": False,
                "completed": True,
                "cycle_id": current_cycle_id,
                "recommended_action": recommended_action,
                "last_completed_stage": last_completed_stage,
                "finished_at": finished_at,
                "paper_only": True,
            })
            cycle_lock_written = True
            cycle_completed = True
            state, status = "CONTROLLED_AUTOMATION_CYCLE_COMPLETE", "PASS"

        except Exception as exc:
            issues.append({
                "code": "CONTROLLED_CYCLE_STAGE_FAILED",
                "blocking": True,
                "detail": str(exc),
            })
            write_json(recovery_path, {
                "stage": "V83.11",
                "recovery_required": True,
                "cycle_id": current_cycle_id,
                "recommended_action": recommended_action,
                "last_completed_stage": last_completed_stage,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "reason": str(exc),
                "paper_only": True,
            })
            recovery_written = True
            state, status = "CONTROLLED_CYCLE_RECOVERY_REQUIRED", "BLOCKED"

    if not recovery_written:
        write_json(recovery_path, {
            "stage": "V83.11",
            "recovery_required": (
                state == "CONTROLLED_CYCLE_RECOVERY_REQUIRED"
            ),
            "cycle_id": current_cycle_id,
            "recommended_action": recommended_action,
            "last_completed_stage": last_completed_stage,
            "observed_at": now_iso,
            "paper_only": True,
        })
        recovery_written = True

    dashboard = {
        "stage": "V83.12",
        "controlled_cycle_state": state,
        "cycle_id": current_cycle_id,
        "recommended_action": recommended_action,
        "orchestrator_ready": orchestrator_ready,
        "cycle_started": cycle_started,
        "cycle_completed": cycle_completed,
        "cycle_recovered": cycle_recovered,
        "last_completed_stage": last_completed_stage,
        "stage_count": len(stage_results),
        "gate_reasons": gate_reasons,
        "max_actions_per_cycle": 1,
        "automatic_repetition_enabled": False,
        "continuous_loop_enabled": False,
        "broker_command_execution_enabled": False,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.09-V83.12",
        "implementation_type": "CONTROLLED_AUTOMATION_CYCLE_FOUNDATION",
        "status": status,
        "state": state,
        "cycle_id": current_cycle_id,
        "recommended_action": recommended_action,
        "orchestrator_ready": orchestrator_ready,
        "execute_cycle_requested": execute_cycle,
        "resume_cycle_requested": resume_cycle,
        "clear_cycle_lock_requested": clear_cycle_lock,
        "active_cycle": active_cycle or (
            cycle_started and not cycle_completed
        ),
        "duplicate_cycle": duplicate_cycle,
        "recovery_available": recovery_available,
        "cycle_started": cycle_started,
        "cycle_completed": cycle_completed,
        "cycle_recovered": cycle_recovered,
        "authorized_action_id": authorized_action_id,
        "dispatcher_succeeded": dispatcher_succeeded,
        "reevaluated_state": reevaluated_state,
        "last_completed_stage": last_completed_stage,
        "stage_count": len(stage_results),
        "stage_results": stage_results,
        "gate_reasons": gate_reasons,
        "cycle_lock_written": cycle_lock_written,
        "cycle_ledger_written": cycle_ledger_written,
        "cycle_report_written": cycle_report_written,
        "recovery_snapshot_written": recovery_written,
        "dashboard_state_written": True,
        "max_actions_per_cycle": 1,
        "automatic_action_authorization_enabled": False,
        "automatic_repetition_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_install_enabled": False,
        "broker_command_execution_enabled": False,
        "paper_only": True,
        "read_only": True,
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
            "V83_13_SUPERVISED_AUTOMATION_RUNNER"
            if state in {
                "CONTROLLED_CYCLE_READY",
                "CONTROLLED_AUTOMATION_CYCLE_COMPLETE",
                "CONTROLLED_CYCLE_WAIT_GATES",
            }
            else "V83_09_TO_V83_12_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SINGLE_CONTROLLED_CYCLE_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
