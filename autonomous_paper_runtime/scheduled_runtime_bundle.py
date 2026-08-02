from __future__ import annotations

import hashlib
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
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _scheduled_id(runtime_id: str, schedule_id: str) -> str:
    digest = hashlib.sha256(f"{runtime_id}|{schedule_id}".encode()).hexdigest()[:24]
    return "scheduled-runtime-" + digest


class ScheduledRuntimeBundle:
    def run(
        self,
        *,
        runtime_result_path: Path,
        runtime_token_path: Path,
        schedule_policy_path: Path,
        resume_snapshot_path: Path,
        recovery_snapshot_path: Path,
        emergency_stop_path: Path,
        scheduled_state_path: Path,
        heartbeat_path: Path,
        recovery_token_path: Path,
        scheduled_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            runtime = _load(runtime_result_path)
        except Exception as exc:
            runtime = {}
            issues.append({"code": "INVALID_RUNTIME_RESULT", "blocking": True, "detail": str(exc)})

        if not runtime:
            issues.append({"code": "RUNTIME_RESULT_NOT_FOUND", "blocking": True, "detail": str(runtime_result_path)})

        status = str(runtime.get("status", "")).upper()
        state = str(runtime.get("state", "")).upper()
        safe = bool(runtime.get("safe_mode_engaged", False))
        ready = bool(runtime.get("autonomous_paper_runtime_ready", False))
        runtime_id = str(runtime.get("runtime_id", "")).strip()
        session_id = str(runtime.get("session_id", "")).strip()

        if status == "BLOCKED" or safe:
            issues.append({"code": "SOURCE_RUNTIME_SAFE_MODE", "blocking": True, "detail": state})

        required = ready or state == "AUTONOMOUS_PAPER_RUNTIME_READY"
        token = schedule = resume = recovery = emergency = {}

        if required:
            for name, path in (
                ("RUNTIME_TOKEN", runtime_token_path),
                ("SCHEDULE_POLICY", schedule_policy_path),
                ("RESUME_SNAPSHOT", resume_snapshot_path),
                ("RECOVERY_SNAPSHOT", recovery_snapshot_path),
            ):
                try:
                    loaded = _load(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({"code": f"INVALID_{name}", "blocking": True, "detail": str(exc)})
                if not loaded:
                    issues.append({"code": f"{name}_NOT_FOUND", "blocking": True, "detail": str(path)})
                if name == "RUNTIME_TOKEN":
                    token = loaded
                elif name == "SCHEDULE_POLICY":
                    schedule = loaded
                elif name == "RESUME_SNAPSHOT":
                    resume = loaded
                else:
                    recovery = loaded

            try:
                emergency = _load(emergency_stop_path)
            except Exception as exc:
                issues.append({"code": "INVALID_EMERGENCY_STOP", "blocking": True, "detail": str(exc)})

        if token and (
            token.get("runtime_id") != runtime_id
            or not bool(token.get("autonomous_paper_runtime_ready", False))
            or bool(token.get("continuous_loop_enabled", True))
            or bool(token.get("actual_submission_allowed", True))
            or bool(token.get("broker_network_allowed", True))
            or bool(token.get("live_trading_enabled", True))
        ):
            issues.append({"code": "RUNTIME_TOKEN_MISMATCH", "blocking": True, "detail": "runtime token contract mismatch"})

        emergency_engaged = bool(emergency.get("engaged", False))
        if emergency_engaged:
            issues.append({"code": "EMERGENCY_STOP_ENGAGED", "blocking": True, "detail": str(emergency.get("reason", "manual stop"))})

        schedule_ready = False
        schedule_id = ""
        if schedule:
            schedule_id = str(schedule.get("schedule_id", "")).strip()
            checks = [
                ("SCHEDULE_ID_MISSING", bool(schedule_id)),
                ("SCHEDULER_DISABLED", bool(schedule.get("enabled", False))),
                ("INVALID_SCHEDULE_INTERVAL", int(schedule.get("interval_seconds", 0)) >= 60),
                ("INVALID_MAX_RUNS", 1 <= int(schedule.get("max_runs_per_invocation", 0)) <= 10),
                ("UNBOUNDED_SCHEDULER_BLOCKED", not bool(schedule.get("unbounded_scheduler", True))),
                ("ACTUAL_SUBMISSION_BLOCKED", not bool(schedule.get("actual_submission_allowed", True))),
                ("BROKER_NETWORK_BLOCKED", not bool(schedule.get("broker_network_allowed", True))),
                ("LIVE_TRADING_BLOCKED", not bool(schedule.get("live_trading_enabled", True))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "schedule policy gate failed"})
            schedule_ready = all(passed for _, passed in checks)

        resume_ready = False
        next_tick = 1
        if resume:
            saved_runtime_id = str(resume.get("runtime_id", "")).strip()
            saved_session_id = str(resume.get("session_id", "")).strip()
            last_completed_tick = int(resume.get("last_completed_tick", 0))
            checks = [
                ("RESUME_RUNTIME_MISMATCH", saved_runtime_id == runtime_id),
                ("RESUME_SESSION_MISMATCH", saved_session_id == session_id),
                ("INVALID_LAST_TICK", last_completed_tick >= 0),
                ("RESUME_STATE_UNVERIFIED", bool(resume.get("resume_state_verified", False))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "resume gate failed"})
            resume_ready = all(passed for _, passed in checks)
            if resume_ready:
                next_tick = last_completed_tick + 1

        recovery_ready = False
        recovery_performed = False
        if recovery:
            checks = [
                ("UNRESOLVED_ORDER_STATE", not bool(recovery.get("unresolved_order_state", False))),
                ("CORRUPTED_LEDGER", not bool(recovery.get("ledger_corrupted", False))),
                ("DUPLICATE_PROCESS", int(recovery.get("runtime_process_count", 0)) <= 1),
                ("RECOVERY_UNVERIFIED", bool(recovery.get("recovery_verified", False))),
                ("HEARTBEAT_TOO_OLD", int(recovery.get("heartbeat_age_seconds", 999999)) <= int(recovery.get("max_heartbeat_age_seconds", 300))),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({"code": code, "blocking": True, "detail": "recovery gate failed"})
            recovery_ready = all(passed for _, passed in checks)
            recovery_performed = bool(recovery.get("restart_detected", False)) and recovery_ready

        blocking = sum(1 for item in issues if item.get("blocking"))
        scheduled_ready = bool(required and token and schedule_ready and resume_ready and recovery_ready and not blocking)

        scheduled_id = ""
        state_written = heartbeat_written = recovery_written = token_written = False
        duplicate_token = False

        if scheduled_ready:
            scheduled_id = _scheduled_id(runtime_id, schedule_id)
            now = datetime.now(timezone.utc).isoformat()
            _write(scheduled_state_path, {
                "stage": "V142.08",
                "scheduled_runtime_id": scheduled_id,
                "runtime_id": runtime_id,
                "session_id": session_id,
                "schedule_id": schedule_id,
                "next_tick": next_tick,
                "max_runs_per_invocation": int(schedule["max_runs_per_invocation"]),
                "state": "SCHEDULED_LOCAL_TICK_READY",
                "created_at": now,
            })
            state_written = True

            _write(heartbeat_path, {
                "stage": "V142.05",
                "scheduled_runtime_id": scheduled_id,
                "status": "SCHEDULE_READY",
                "heartbeat_at": now,
                "interval_seconds": int(schedule["interval_seconds"]),
            })
            heartbeat_written = True

            _write(recovery_token_path, {
                "stage": "V142.07",
                "scheduled_runtime_id": scheduled_id,
                "recovery_ready": True,
                "recovery_performed": recovery_performed,
                "resume_tick": next_tick,
                "created_at": now,
            })
            recovery_written = True

            scheduled_token = {
                "stage_range": "V142.05-V142.08",
                "scheduled_runtime_id": scheduled_id,
                "runtime_id": runtime_id,
                "session_id": session_id,
                "schedule_id": schedule_id,
                "scheduled_runtime_ready": True,
                "automatic_recovery_ready": True,
                "session_resume_ready": True,
                "continuous_loop_enabled": False,
                "actual_submission_allowed": False,
                "broker_network_allowed": False,
                "live_trading_enabled": False,
                "created_at": now,
            }

            if scheduled_token_path.exists():
                existing = _load(scheduled_token_path)
                if existing.get("scheduled_runtime_id") == scheduled_id:
                    duplicate_token = True
                else:
                    issues.append({"code": "SCHEDULED_TOKEN_CONFLICT", "blocking": True, "detail": "another schedule owns the token"})
            else:
                _write(scheduled_token_path, scheduled_token)
                token_written = True

        blocking = sum(1 for item in issues if item.get("blocking"))
        safe_mode = blocking > 0
        final_ready = bool(
            scheduled_ready
            and state_written
            and heartbeat_written
            and recovery_written
            and (token_written or duplicate_token)
            and not safe_mode
        )

        if emergency_engaged:
            out_state, out_status = "SCHEDULED_RUNTIME_EMERGENCY_STOP", "BLOCKED"
        elif safe_mode:
            out_state, out_status = "SCHEDULED_RUNTIME_SAFE_MODE", "BLOCKED"
        elif final_ready:
            out_state, out_status = "AUTONOMOUS_RUNTIME_SCHEDULE_READY", "PASS"
        else:
            out_state, out_status = "WAIT_AUTONOMOUS_PAPER_RUNTIME", "PASS"

        result = {
            "stage_range": "V142.05-V142.08",
            "implementation_type": "ULTRA_FAST_SCHEDULED_RUNTIME_RECOVERY",
            "status": out_status,
            "state": out_state,
            "runtime_id": runtime_id,
            "session_id": session_id,
            "scheduled_runtime_id": scheduled_id,
            "schedule_ready": schedule_ready,
            "session_resume_ready": resume_ready,
            "automatic_recovery_ready": recovery_ready,
            "recovery_performed": recovery_performed,
            "next_tick": next_tick,
            "scheduled_state_written": state_written,
            "scheduled_heartbeat_written": heartbeat_written,
            "recovery_token_written": recovery_written,
            "scheduled_token_written": token_written,
            "duplicate_scheduled_token": duplicate_token,
            "scheduled_runtime_ready": final_ready,
            "continuous_loop_enabled": False,
            "emergency_stop_engaged": emergency_engaged,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": "V143_FINAL_PRODUCTION_RELEASE" if final_ready else "V142_05_TO_V142_08_WAIT_RUNTIME",
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "live_trading_enabled": False,
            "validation_mode": "LOCAL_SCHEDULED_RUNTIME_ONLY",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
