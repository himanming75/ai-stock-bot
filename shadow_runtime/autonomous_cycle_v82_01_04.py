from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


def cycle_id(seed: str) -> str:
    return "shadow-cycle-" + hashlib.sha256(seed.encode()).hexdigest()[:20]


def run_autonomous_shadow_cycle(
    *,
    policy_path: Path,
    foundation_result_path: Path,
    execution_result_path: Path,
    portfolio_result_path: Path,
    cycle_lock_path: Path,
    cycle_ledger_path: Path,
    dashboard_path: Path,
    recovery_path: Path,
    result_path: Path,
    execute_cycle: bool = False,
    stage_callbacks: dict[str, Callable[[], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    policy = load_json(policy_path)
    foundation = load_json(foundation_result_path)
    execution = load_json(execution_result_path)
    portfolio = load_json(portfolio_result_path)
    issues: list[dict[str, Any]] = []

    checks = (
        ("SHADOW_ONLY_REQUIRED", bool(policy.get("shadow_only", False))),
        ("SINGLE_CYCLE_ONLY_REQUIRED", bool(policy.get("single_cycle_only", False))),
        ("BROKER_WRITE_MUST_BE_DISABLED", not bool(policy.get("broker_write_enabled", True))),
        ("LIVE_TRADING_MUST_BE_DISABLED", not bool(policy.get("live_trading_enabled", True))),
        ("NETWORK_MUST_BE_DISABLED", not bool(policy.get("network_enabled", True))),
    )
    for code, passed in checks:
        if not passed:
            issues.append({"code": code, "blocking": True})

    existing_lock = load_json(cycle_lock_path)
    duplicate_cycle = bool(existing_lock.get("active", False))
    if execute_cycle and duplicate_cycle:
        issues.append({
            "code": "DUPLICATE_CYCLE_BLOCKED",
            "blocking": True,
            "detail": existing_lock.get("cycle_id", ""),
        })

    foundation_ready = foundation.get("state") == "SHADOW_TRADING_READY"
    execution_ready = execution.get("state") in {
        "SHADOW_EXECUTION_FILLED",
        "SHADOW_EXECUTION_NO_ACTION",
    }
    portfolio_ready = portfolio.get("state") in {
        "SHADOW_PORTFOLIO_UPDATED",
        "SHADOW_PORTFOLIO_NO_CHANGE",
    }

    blocking = any(i.get("blocking") for i in issues)
    now = datetime.now(timezone.utc).isoformat()
    cid = ""
    stages: list[dict[str, Any]] = []
    cycle_completed = False
    recovery_ready = False

    if blocking:
        state, status = "AUTONOMOUS_SHADOW_CYCLE_SAFE_MODE", "BLOCKED"
    elif not execute_cycle:
        state, status = "AUTONOMOUS_SHADOW_CYCLE_READY", "PASS"
    elif not foundation_ready:
        state, status = "WAIT_SHADOW_FOUNDATION", "PASS"
    else:
        cid = cycle_id(now)
        write_json(cycle_lock_path, {
            "active": True,
            "cycle_id": cid,
            "started_at": now,
            "shadow_only": True,
        })
        callbacks = stage_callbacks or {}
        ordered = [
            "SNAPSHOT",
            "SIGNAL",
            "EXECUTION",
            "PORTFOLIO",
            "RISK",
            "REPORT",
        ]
        start = time.perf_counter()
        try:
            for name in ordered:
                stage_start = time.perf_counter()
                payload = callbacks[name]() if name in callbacks else {
                    "status": "PASS",
                    "mode": "LOCAL_PLAN_ONLY",
                }
                stages.append({
                    "stage": name,
                    "status": payload.get("status", "PASS"),
                    "elapsed_ms": round((time.perf_counter() - stage_start) * 1000, 3),
                })
                if payload.get("status") not in {"PASS", "WAIT"}:
                    raise RuntimeError(f"{name} stage failed")
            cycle_completed = True
            state, status = "AUTONOMOUS_SHADOW_CYCLE_COMPLETE", "PASS"
        except Exception as exc:
            issues.append({
                "code": "CYCLE_STAGE_FAILED",
                "blocking": True,
                "detail": str(exc),
            })
            state, status = "AUTONOMOUS_SHADOW_CYCLE_RECOVERY_REQUIRED", "BLOCKED"
            recovery_ready = True
        elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
        finished = datetime.now(timezone.utc).isoformat()
        append_jsonl(cycle_ledger_path, {
            "cycle_id": cid,
            "started_at": now,
            "finished_at": finished,
            "elapsed_ms": elapsed_ms,
            "completed": cycle_completed,
            "stages": stages,
            "shadow_only": True,
        })
        write_json(cycle_lock_path, {
            "active": False,
            "cycle_id": cid,
            "finished_at": finished,
            "completed": cycle_completed,
            "shadow_only": True,
        })

    write_json(recovery_path, {
        "cycle_id": cid,
        "recovery_ready": recovery_ready,
        "last_safe_stage": stages[-1]["stage"] if stages else "",
        "shadow_only": True,
        "observed_at": now,
    })

    dashboard = {
        "stage": "V82.04",
        "cycle_state": state,
        "cycle_id": cid,
        "cycle_completed": cycle_completed,
        "stage_count": len(stages),
        "last_stage": stages[-1]["stage"] if stages else "",
        "foundation_ready": foundation_ready,
        "execution_ready": execution_ready,
        "portfolio_ready": portfolio_ready,
        "read_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.01-V82.04",
        "implementation_type": "AUTONOMOUS_SHADOW_CYCLE_FOUNDATION",
        "status": status,
        "state": state,
        "cycle_execute_requested": execute_cycle,
        "cycle_id": cid,
        "cycle_completed": cycle_completed,
        "stage_count": len(stages),
        "stages": stages,
        "foundation_ready": foundation_ready,
        "execution_ready": execution_ready,
        "portfolio_ready": portfolio_ready,
        "duplicate_cycle": duplicate_cycle,
        "recovery_ready": recovery_ready,
        "cycle_ledger_written": execute_cycle and bool(cid),
        "dashboard_state_written": True,
        "recovery_snapshot_written": True,
        "single_cycle_only": True,
        "continuous_loop_enabled": False,
        "windows_task_install_enabled": False,
        "shadow_only": True,
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
        "blocking_issue_count": sum(1 for i in issues if i.get("blocking")),
        "issues": issues,
        "next_phase": (
            "V82_05_AUTONOMOUS_SHADOW_SCHEDULER"
            if state in {"AUTONOMOUS_SHADOW_CYCLE_READY", "AUTONOMOUS_SHADOW_CYCLE_COMPLETE"}
            else "V82_01_TO_V82_04_WAIT_OR_RECOVER"
        ),
        "observed_at": now,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
