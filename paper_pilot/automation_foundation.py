from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


class PaperPilotAutomationFoundation:
    def run(
        self,
        *,
        policy_path: Path,
        foundation_result_path: Path,
        session_monitor_result_path: Path,
        performance_result_path: Path,
        risk_result_path: Path,
        snapshot_collector_result_path: Path,
        cycle_plan_path: Path,
        recovery_gate_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        execute_cycle: bool = False,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        loaded: dict[str, dict[str, Any]] = {}

        for name, path in (
            ("AUTOMATION_POLICY", policy_path),
            ("FOUNDATION_RESULT", foundation_result_path),
            ("SESSION_MONITOR_RESULT", session_monitor_result_path),
            ("PERFORMANCE_RESULT", performance_result_path),
            ("RISK_RESULT", risk_result_path),
            ("SNAPSHOT_COLLECTOR_RESULT", snapshot_collector_result_path),
        ):
            try:
                value = _load(path)
            except Exception as exc:
                value = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if not value:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = value

        policy = loaded["AUTOMATION_POLICY"]
        foundation = loaded["FOUNDATION_RESULT"]
        monitor = loaded["SESSION_MONITOR_RESULT"]
        performance = loaded["PERFORMANCE_RESULT"]
        risk = loaded["RISK_RESULT"]
        snapshot_result = loaded["SNAPSHOT_COLLECTOR_RESULT"]

        policy_ready = False
        if policy:
            checks = [
                ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
                ("SINGLE_CYCLE_REQUIRED", bool(policy.get("single_cycle_only", False))),
                (
                    "CONTINUOUS_LOOP_MUST_BE_DISABLED",
                    not bool(policy.get("continuous_loop_enabled", True)),
                ),
                (
                    "WINDOWS_TASK_MUST_BE_DISABLED",
                    not bool(policy.get("windows_task_install_enabled", True)),
                ),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "ORDER_SUBMISSION_MUST_BE_DISABLED",
                    not bool(policy.get("order_submission_enabled", True)),
                ),
                (
                    "MAX_STEPS_INVALID",
                    int(policy.get("maximum_steps_per_cycle", 0)) == 4,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "automation policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        pilot_started = bool(foundation.get("pilot_started", False))
        pilot_state = str(foundation.get("state", ""))
        pilot_id = str(foundation.get("pilot_id", "")).strip()
        session_id = str(foundation.get("session_id", "")).strip()

        monitor_state = str(monitor.get("state", ""))
        session_health = str(monitor.get("health_status", "WAITING")).upper()
        performance_state = str(performance.get("state", ""))
        risk_state = str(risk.get("state", ""))
        emergency_stop_required = bool(
            risk.get("emergency_stop_required", False)
        )
        snapshot_ready = bool(
            snapshot_result.get("snapshot_written", False)
            and snapshot_result.get("status") == "PASS"
            and not snapshot_result.get("safe_mode_engaged", False)
        )

        recovery_reasons: list[str] = []
        if not snapshot_ready:
            recovery_reasons.append("ACTUAL_PAPER_SNAPSHOT_NOT_READY")
        if emergency_stop_required:
            recovery_reasons.append("EMERGENCY_STOP_REQUIRED")
        if session_health in {"STOP_REQUIRED", "TIMEOUT", "DEGRADED"}:
            recovery_reasons.append("SESSION_HEALTH_UNSAFE")
        if bool(monitor.get("controlled_stop_required", False)):
            recovery_reasons.append("CONTROLLED_STOP_REQUIRED")
        if bool(foundation.get("recovery_required", False)):
            recovery_reasons.append("ORDER_RECOVERY_REQUIRED")
        if int(foundation.get("open_order_count", 0) or 0) > 0:
            recovery_reasons.append("OPEN_ORDERS_PRESENT")

        recovery_gate_clear = not recovery_reasons

        steps = [
            {
                "order": 1,
                "name": "ACTUAL_PAPER_SNAPSHOT_REFRESH",
                "script": "RUN_DASH2_05_REFRESH_ACTUAL_PAPER_SNAPSHOT.ps1",
                "requires_explicit_network_switch": True,
                "ready": True,
            },
            {
                "order": 2,
                "name": "PILOT_HEARTBEAT",
                "script": "RUN_OP4_05_TO_OP4_08_SESSION_MONITOR.ps1",
                "requires_explicit_network_switch": False,
                "ready": pilot_started,
            },
            {
                "order": 3,
                "name": "PERFORMANCE_COLLECTION",
                "script": "RUN_OP4_09_TO_OP4_12_PERFORMANCE.ps1",
                "requires_explicit_network_switch": False,
                "ready": pilot_started and snapshot_ready,
            },
            {
                "order": 4,
                "name": "RISK_MONITOR",
                "script": "RUN_OP4_13_TO_OP4_16_RISK_MONITOR.ps1",
                "requires_explicit_network_switch": False,
                "ready": snapshot_ready,
            },
        ]

        cycle_ready = bool(
            policy_ready
            and pilot_started
            and recovery_gate_clear
            and all(step["ready"] for step in steps)
            and not any(i.get("blocking") for i in issues)
        )

        now = datetime.now(timezone.utc).isoformat()

        _write(cycle_plan_path, {
            "stage": "OP4.17",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "windows_task_install_enabled": False,
            "steps": steps,
            "cycle_ready": cycle_ready,
            "created_at": now,
        })

        _write(recovery_gate_path, {
            "stage": "OP4.18-OP4.19",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "pilot_state": pilot_state,
            "monitor_state": monitor_state,
            "performance_state": performance_state,
            "risk_state": risk_state,
            "snapshot_ready": snapshot_ready,
            "session_health": session_health,
            "emergency_stop_required": emergency_stop_required,
            "recovery_gate_clear": recovery_gate_clear,
            "recovery_reasons": recovery_reasons,
            "broker_action_performed": False,
            "created_at": now,
        })

        cycle_executed = False
        if execute_cycle and cycle_ready:
            # Foundation intentionally writes only an execution authorization record.
            # It does not invoke child scripts, network, or broker operations.
            cycle_executed = True

        if any(i.get("blocking") for i in issues):
            state, status = "PILOT_AUTOMATION_SAFE_MODE", "BLOCKED"
        elif not pilot_started:
            state, status = "WAIT_PILOT_START", "PASS"
        elif not recovery_gate_clear:
            state, status = "PILOT_AUTOMATION_RECOVERY_BLOCKED", "PASS"
        elif execute_cycle and cycle_ready:
            state, status = "PILOT_AUTOMATION_CYCLE_AUTHORIZED", "PASS"
        elif cycle_ready:
            state, status = "PILOT_AUTOMATION_READY", "PASS"
        else:
            state, status = "WAIT_AUTOMATION_PREREQUISITES", "PASS"

        _write(dashboard_state_path, {
            "stage": "OP4.20",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "automation_state": state,
            "cycle_ready": cycle_ready,
            "cycle_execute_requested": execute_cycle,
            "cycle_authorized": cycle_executed,
            "snapshot_ready": snapshot_ready,
            "session_health": session_health,
            "emergency_stop_required": emergency_stop_required,
            "recovery_gate_clear": recovery_gate_clear,
            "recovery_reasons": recovery_reasons,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now,
        })

        blocking = sum(1 for item in issues if item.get("blocking"))
        result = {
            "stage_range": "OP4.17-OP4.20",
            "implementation_type": "PAPER_PILOT_AUTOMATION_FOUNDATION",
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "snapshot_ready": snapshot_ready,
            "session_health": session_health,
            "performance_state": performance_state,
            "risk_state": risk_state,
            "emergency_stop_required": emergency_stop_required,
            "recovery_gate_clear": recovery_gate_clear,
            "recovery_reasons": recovery_reasons,
            "cycle_ready": cycle_ready,
            "cycle_execute_requested": execute_cycle,
            "cycle_authorized": cycle_executed,
            "cycle_plan_written": True,
            "recovery_gate_written": True,
            "dashboard_state_written": True,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "windows_task_install_enabled": False,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "position_close_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": blocking > 0,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP5_01_MULTI_DAY_PAPER_VALIDATION"
                if cycle_ready
                else "OP4_17_TO_OP4_20_WAIT_AUTOMATION_GATE"
            ),
            "validation_mode": "LOCAL_SINGLE_CYCLE_AUTOMATION_PLAN_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
