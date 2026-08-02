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


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class PaperPilotSessionMonitor:
    def run(
        self,
        *,
        policy_path: Path,
        foundation_result_path: Path,
        pilot_lock_path: Path,
        pilot_session_path: Path,
        heartbeat_path: Path,
        health_path: Path,
        controlled_stop_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        write_heartbeat: bool = False,
        request_controlled_stop: bool = False,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded: dict[str, dict[str, Any]] = {}
        for name, path, required in (
            ("MONITOR_POLICY", policy_path, True),
            ("FOUNDATION_RESULT", foundation_result_path, True),
            ("PILOT_LOCK", pilot_lock_path, False),
            ("PILOT_SESSION", pilot_session_path, False),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if required and not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["MONITOR_POLICY"]
        foundation = loaded["FOUNDATION_RESULT"]
        lock = loaded["PILOT_LOCK"]
        session = loaded["PILOT_SESSION"]

        policy_ready = False
        if policy:
            checks = [
                (
                    "PAPER_ONLY_REQUIRED",
                    bool(policy.get("paper_only", False)),
                ),
                (
                    "READ_ONLY_MONITOR_REQUIRED",
                    bool(policy.get("read_only_monitor", False)),
                ),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "HEARTBEAT_INTERVAL_INVALID",
                    5 <= int(policy.get("heartbeat_interval_seconds", 0)) <= 300,
                ),
                (
                    "TIMEOUT_INVALID",
                    int(policy.get("session_timeout_seconds", 0))
                    > int(policy.get("heartbeat_interval_seconds", 0)),
                ),
                (
                    "MAX_TIMEOUT_INVALID",
                    int(policy.get("session_timeout_seconds", 0)) <= 3600,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "session monitor policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        foundation_started = bool(
            foundation.get("pilot_started", False)
        )
        pilot_id = str(
            foundation.get("pilot_id", lock.get("pilot_id", ""))
        ).strip()
        session_id = str(
            foundation.get("session_id", lock.get("session_id", ""))
        ).strip()

        lock_active = bool(lock.get("active", False))
        session_running = (
            str(session.get("status", "")).upper() == "RUNNING"
        )
        active_session_ready = bool(
            foundation_started
            and pilot_id
            and session_id
            and lock_active
            and session_running
            and lock.get("pilot_id") == pilot_id
            and lock.get("session_id") == session_id
            and session.get("pilot_id") == pilot_id
            and session.get("session_id") == session_id
        )

        if foundation_started and not active_session_ready:
            issues.append({
                "code": "PILOT_SESSION_IDENTITY_MISMATCH",
                "blocking": True,
                "detail": pilot_id,
            })

        now = (
            _parse_time(observed_at)
            if observed_at
            else datetime.now(timezone.utc)
        )
        if now is None:
            issues.append({
                "code": "OBSERVED_AT_INVALID",
                "blocking": True,
                "detail": str(observed_at),
            })
            now = datetime.now(timezone.utc)

        existing_heartbeat = {}
        if heartbeat_path.exists():
            try:
                existing_heartbeat = _load(heartbeat_path)
            except Exception as exc:
                issues.append({
                    "code": "INVALID_HEARTBEAT",
                    "blocking": True,
                    "detail": str(exc),
                })

        heartbeat_written = False
        tick_number = int(
            existing_heartbeat.get("tick_number", 0) or 0
        )
        if (
            write_heartbeat
            and active_session_ready
            and policy_ready
            and not any(i.get("blocking") for i in issues)
        ):
            tick_number += 1
            _write(heartbeat_path, {
                "stage": "OP4.05",
                "pilot_id": pilot_id,
                "session_id": session_id,
                "heartbeat_id": (
                    f"{session_id}-heartbeat-{tick_number:06d}"
                ),
                "tick_number": tick_number,
                "observed_at": now.isoformat(),
                "paper_only": True,
                "broker_write_enabled": False,
            })
            heartbeat_written = True
            existing_heartbeat = _load(heartbeat_path)

        heartbeat_time = _parse_time(
            str(existing_heartbeat.get("observed_at", ""))
        )
        heartbeat_age_seconds = (
            max(0, int((now - heartbeat_time).total_seconds()))
            if heartbeat_time
            else None
        )
        timeout_seconds = int(
            policy.get("session_timeout_seconds", 0) or 0
        )
        timeout_detected = bool(
            active_session_ready
            and (
                heartbeat_age_seconds is None
                or heartbeat_age_seconds > timeout_seconds
            )
        )

        emergency_stop = bool(
            foundation.get("emergency_stop_engaged", False)
        )
        duplicate_runtime = bool(
            foundation.get("duplicate_pilot", False)
        )

        stop_reasons = []
        if timeout_detected:
            stop_reasons.append("SESSION_TIMEOUT")
        if emergency_stop:
            stop_reasons.append("EMERGENCY_STOP")
        if duplicate_runtime:
            stop_reasons.append("DUPLICATE_RUNTIME")
        if request_controlled_stop:
            stop_reasons.append("MANUAL_CONTROLLED_STOP")

        controlled_stop_required = bool(
            active_session_ready and stop_reasons
        )
        controlled_stop_written = False
        if (
            controlled_stop_required
            and not any(i.get("blocking") for i in issues)
        ):
            _write(controlled_stop_path, {
                "stage": "OP4.08",
                "pilot_id": pilot_id,
                "session_id": session_id,
                "stop_reasons": stop_reasons,
                "controlled_stop_required": True,
                "broker_action_performed": False,
                "order_action_performed": False,
                "created_at": now.isoformat(),
            })
            controlled_stop_written = True

        if not foundation_started:
            health_status = "WAITING"
        elif controlled_stop_required:
            health_status = "STOP_REQUIRED"
        elif timeout_detected:
            health_status = "TIMEOUT"
        elif active_session_ready and heartbeat_age_seconds is not None:
            warning_threshold = int(
                policy.get("heartbeat_warning_seconds", 0) or 0
            )
            health_status = (
                "WARNING"
                if heartbeat_age_seconds > warning_threshold
                else "HEALTHY"
            )
        elif active_session_ready:
            health_status = "WARNING"
        else:
            health_status = "DEGRADED"

        health_written = False
        _write(health_path, {
            "stage": "OP4.07",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "health_status": health_status,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "heartbeat_warning_seconds": int(
                policy.get("heartbeat_warning_seconds", 0) or 0
            ),
            "session_timeout_seconds": timeout_seconds,
            "timeout_detected": timeout_detected,
            "controlled_stop_required": controlled_stop_required,
            "stop_reasons": stop_reasons,
            "observed_at": now.isoformat(),
            "paper_only": True,
            "read_only": True,
        })
        health_written = True

        if any(i.get("blocking") for i in issues):
            state, status = (
                "PAPER_SESSION_MONITOR_SAFE_MODE",
                "BLOCKED",
            )
        elif not foundation_started:
            state, status = (
                "WAIT_PILOT_START",
                "PASS",
            )
        elif controlled_stop_required:
            state, status = (
                "PAPER_SESSION_CONTROLLED_STOP_REQUIRED",
                "PASS",
            )
        elif health_status == "HEALTHY":
            state, status = (
                "PAPER_SESSION_HEALTHY",
                "PASS",
            )
        else:
            state, status = (
                "PAPER_SESSION_MONITORING",
                "PASS",
            )

        _write(dashboard_state_path, {
            "stage": "OP4.05-OP4.08",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "monitor_state": state,
            "health_status": health_status,
            "heartbeat_written": heartbeat_written,
            "tick_number": tick_number,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "timeout_detected": timeout_detected,
            "controlled_stop_required": controlled_stop_required,
            "controlled_stop_written": controlled_stop_written,
            "stop_reasons": stop_reasons,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now.isoformat(),
        })

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP4.05-OP4.08",
            "implementation_type": (
                "PAPER_PILOT_SESSION_MONITOR"
            ),
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "session_id": session_id,
            "foundation_started": foundation_started,
            "active_session_ready": active_session_ready,
            "heartbeat_requested": write_heartbeat,
            "heartbeat_written": heartbeat_written,
            "tick_number": tick_number,
            "heartbeat_age_seconds": heartbeat_age_seconds,
            "timeout_detected": timeout_detected,
            "health_status": health_status,
            "health_written": health_written,
            "controlled_stop_requested": request_controlled_stop,
            "controlled_stop_required": controlled_stop_required,
            "controlled_stop_written": controlled_stop_written,
            "stop_reasons": stop_reasons,
            "dashboard_state_written": True,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "replace_enabled": False,
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
                "OP4_09_PAPER_PERFORMANCE_COLLECTOR"
                if foundation_started and not controlled_stop_required
                else "OP4_05_TO_OP4_08_WAIT_OR_STOP"
            ),
            "validation_mode": (
                "LOCAL_PAPER_SESSION_MONITOR_ONLY"
            ),
            "observed_at": now.isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
