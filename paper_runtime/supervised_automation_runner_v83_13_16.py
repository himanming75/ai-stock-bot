
from __future__ import annotations
import json, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")

def run_supervised_automation_runner(
    *,
    controlled_cycle_result_path: Path,
    orchestrator_result_path: Path,
    dispatcher_result_path: Path,
    risk_result_path: Path,
    policy_path: Path,
    runner_lock_path: Path,
    runner_ledger_path: Path,
    runner_summary_path: Path,
    recovery_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_runner: bool = False,
    clear_runner_lock: bool = False,
    cycle_executor: Callable[[int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    sources = {}
    for name, path in {
        "controlled_cycle": controlled_cycle_result_path,
        "orchestrator": orchestrator_result_path,
        "dispatcher": dispatcher_result_path,
        "risk": risk_result_path,
        "policy": policy_path,
    }.items():
        try:
            sources[name] = load_json(path)
        except Exception as exc:
            sources[name] = {}
            issues.append({"code": f"INVALID_{name.upper()}_INPUT", "blocking": True, "detail": str(exc)})

    policy = sources["policy"]
    if not policy:
        issues.append({"code": "SUPERVISED_RUNNER_POLICY_NOT_FOUND", "blocking": True, "detail": str(policy_path)})

    max_cycles = int(policy.get("max_cycles_per_run", 3) or 3)
    max_failures = int(policy.get("max_consecutive_failures", 1) or 1)
    pause_seconds = float(policy.get("pause_seconds", 0) or 0)

    checks = (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED", not bool(policy.get("broker_write_enabled", True))),
        ("ORDER_SUBMISSION_MUST_BE_DISABLED", not bool(policy.get("order_submission_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled", True))),
        ("CONTINUOUS_LOOP_MUST_BE_DISABLED", not bool(policy.get("continuous_loop_enabled", True))),
        ("MAX_CYCLES_MUST_BE_BOUNDED", 1 <= max_cycles <= 10),
        ("CONSECUTIVE_FAILURE_LIMIT_REQUIRED", 1 <= max_failures <= max_cycles),
    )
    for code, passed in checks:
        if not passed:
            issues.append({"code": code, "blocking": True, "detail": "runner safety policy failed"})

    risk_clear = sources["risk"].get("state") == "SHADOW_RISK_CLEAR"
    if not risk_clear:
        issues.append({"code": "RISK_NOT_CLEAR", "blocking": True, "detail": str(sources["risk"].get("state", ""))})

    lock = load_json(runner_lock_path)
    active_runner = bool(lock.get("active", False))
    duplicate_runner = execute_runner and active_runner
    if duplicate_runner:
        issues.append({"code": "DUPLICATE_SUPERVISED_RUNNER_BLOCKED", "blocking": True, "detail": str(lock.get("runner_id", ""))})

    runner_started = runner_completed = False
    lock_written = ledger_written = summary_written = recovery_written = False
    cycles = []
    successful = failed = skipped = consecutive = 0
    stop_reason = ""
    runner_id = str(lock.get("runner_id", ""))
    blocking = any(x.get("blocking") for x in issues)

    if blocking:
        state, status = "SUPERVISED_RUNNER_SAFE_MODE", "BLOCKED"
    elif clear_runner_lock:
        write_json(runner_lock_path, {"active": False, "runner_id": "", "cleared_at": now_iso, "paper_only": True})
        lock_written = True
        state, status = "SUPERVISED_RUNNER_LOCK_CLEARED", "PASS"
    elif not execute_runner:
        state, status = "SUPERVISED_RUNNER_READY", "PASS"
    else:
        runner_id = "supervised-runner-" + now.strftime("%Y%m%d%H%M%S%f")
        write_json(runner_lock_path, {"active": True, "runner_id": runner_id, "max_cycles": max_cycles, "started_at": now_iso, "paper_only": True})
        lock_written = runner_started = True
        started = time.perf_counter()
        executor = cycle_executor or (lambda i: {"status": "PASS", "state": "CONTROLLED_AUTOMATION_CYCLE_COMPLETE", "cycle_index": i})

        for index in range(1, max_cycles + 1):
            if load_json(risk_result_path).get("state") != "SHADOW_RISK_CLEAR":
                stop_reason = "RISK_BECAME_UNSAFE"
                skipped = max_cycles - index + 1
                break

            orch = load_json(orchestrator_result_path)
            action = str(orch.get("recommended_action", ""))
            if action in {"", "WAIT", "WAIT_NEXT_MARKET_OPEN"}:
                stop_reason = "NO_ACTION_READY"
                skipped = max_cycles - index + 1
                break

            payload = executor(index)
            cstatus = str(payload.get("status", "PASS"))
            cstate = str(payload.get("state", ""))
            success = cstatus == "PASS" and cstate in {
                "CONTROLLED_AUTOMATION_CYCLE_COMPLETE",
                "CONTROLLED_CYCLE_READY",
                "CONTROLLED_CYCLE_WAIT_GATES",
            }
            record = {
                "stage": "V83.14-V83.15",
                "runner_id": runner_id,
                "cycle_index": index,
                "cycle_status": cstatus,
                "cycle_state": cstate,
                "success": success,
                "recommended_action_before": action,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "paper_only": True,
            }
            cycles.append(record)
            append_jsonl(runner_ledger_path, {**record, "event": "SUPERVISED_CYCLE_FINISHED"})
            ledger_written = True

            if success:
                successful += 1
                consecutive = 0
            else:
                failed += 1
                consecutive += 1

            if consecutive >= max_failures:
                stop_reason = "CONSECUTIVE_FAILURE_LIMIT_REACHED"
                skipped = max_cycles - index
                break

            if pause_seconds > 0 and index < max_cycles:
                time.sleep(pause_seconds)

        if not stop_reason:
            stop_reason = "MAX_CYCLES_REACHED"

        summary = {
            "stage": "V83.16",
            "runner_id": runner_id,
            "max_cycles": max_cycles,
            "attempted_cycles": len(cycles),
            "successful_cycles": successful,
            "failed_cycles": failed,
            "skipped_cycles": skipped,
            "stop_reason": stop_reason,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "cycles": cycles,
            "started_at": now_iso,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "paper_only": True,
        }
        write_json(runner_summary_path, summary)
        summary_written = True
        write_json(runner_lock_path, {"active": False, "runner_id": runner_id, "completed": True, "stop_reason": stop_reason, "paper_only": True})
        lock_written = runner_completed = True

        if failed:
            write_json(recovery_path, {"recovery_required": True, "runner_id": runner_id, "failed_cycles": failed, "stop_reason": stop_reason, "paper_only": True})
            recovery_written = True
            state, status = "SUPERVISED_RUNNER_COMPLETED_WITH_FAILURES", "BLOCKED"
        else:
            state, status = "SUPERVISED_RUNNER_COMPLETE", "PASS"

    if not recovery_written:
        write_json(recovery_path, {"recovery_required": state in {"SUPERVISED_RUNNER_SAFE_MODE", "SUPERVISED_RUNNER_COMPLETED_WITH_FAILURES"}, "runner_id": runner_id, "observed_at": now_iso, "paper_only": True})
        recovery_written = True

    dashboard = {
        "stage": "V83.16",
        "supervised_runner_state": state,
        "runner_id": runner_id,
        "runner_started": runner_started,
        "runner_completed": runner_completed,
        "max_cycles": max_cycles,
        "attempted_cycles": len(cycles),
        "successful_cycles": successful,
        "failed_cycles": failed,
        "skipped_cycles": skipped,
        "stop_reason": stop_reason,
        "risk_clear": risk_clear,
        "operator_supervision_required": True,
        "automatic_repetition_enabled": False,
        "continuous_loop_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "paper_only": True,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.13-V83.16",
        "implementation_type": "SUPERVISED_AUTOMATION_RUNNER_FOUNDATION",
        "status": status,
        "state": state,
        "runner_id": runner_id,
        "execute_runner_requested": execute_runner,
        "clear_runner_lock_requested": clear_runner_lock,
        "active_runner": active_runner or (runner_started and not runner_completed),
        "duplicate_runner": duplicate_runner,
        "runner_started": runner_started,
        "runner_completed": runner_completed,
        "max_cycles": max_cycles,
        "max_consecutive_failures": max_failures,
        "attempted_cycles": len(cycles),
        "successful_cycles": successful,
        "failed_cycles": failed,
        "skipped_cycles": skipped,
        "consecutive_failures": consecutive,
        "stop_reason": stop_reason,
        "cycle_results": cycles,
        "runner_lock_written": lock_written,
        "runner_ledger_written": ledger_written,
        "runner_summary_written": summary_written,
        "recovery_snapshot_written": recovery_written,
        "dashboard_state_written": True,
        "operator_supervision_required": True,
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
        "blocking_issue_count": sum(1 for x in issues if x.get("blocking")),
        "issues": issues,
        "next_phase": "V83_17_SCHEDULED_SUPERVISED_RUNNER" if state in {
            "SUPERVISED_RUNNER_READY", "SUPERVISED_RUNNER_COMPLETE", "SUPERVISED_RUNNER_LOCK_CLEARED"
        } else "V83_13_TO_V83_16_WAIT_OR_RECOVER",
        "validation_mode": "LOCAL_BOUNDED_SUPERVISED_RUNNER_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
