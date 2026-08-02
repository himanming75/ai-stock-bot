from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _runtime_id(release_id: str, session_id: str) -> str:
    value = f"{release_id}|{session_id}"
    return "paper-runtime-" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


class AutonomousPaperRuntimeBundle:
    def run(
        self,
        *,
        release_result_path: Path,
        release_token_path: Path,
        runtime_policy_path: Path,
        watchdog_snapshot_path: Path,
        emergency_stop_path: Path,
        runtime_lock_path: Path,
        heartbeat_path: Path,
        tick_result_path: Path,
        runtime_token_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        try:
            release_result = _load_json(release_result_path)
        except Exception as exc:
            release_result = {}
            issues.append({
                "code": "INVALID_RELEASE_RESULT",
                "blocking": True,
                "detail": str(exc),
            })

        if not release_result:
            issues.append({
                "code": "RELEASE_RESULT_NOT_FOUND",
                "blocking": True,
                "detail": str(release_result_path),
            })

        source_status = str(release_result.get("status", "")).upper()
        source_state = str(release_result.get("state", "")).upper()
        source_safe = bool(release_result.get("safe_mode_engaged", False))
        release_ready = bool(
            release_result.get("paper_production_release_ready", False)
        )
        release_id = str(release_result.get("release_id", "")).strip()
        engine_id = str(release_result.get("engine_id", "")).strip()

        if source_status == "BLOCKED" or source_safe:
            issues.append({
                "code": "SOURCE_RELEASE_SAFE_MODE",
                "blocking": True,
                "detail": source_state,
            })

        required = release_ready or source_state == "PAPER_PRODUCTION_RELEASE_READY"
        release_token: dict[str, Any] = {}
        policy: dict[str, Any] = {}
        watchdog: dict[str, Any] = {}
        emergency: dict[str, Any] = {}

        if required:
            for code, path in (
                ("RELEASE_TOKEN", release_token_path),
                ("RUNTIME_POLICY", runtime_policy_path),
                ("WATCHDOG_SNAPSHOT", watchdog_snapshot_path),
            ):
                try:
                    loaded = _load_json(path)
                except Exception as exc:
                    loaded = {}
                    issues.append({
                        "code": f"INVALID_{code}",
                        "blocking": True,
                        "detail": str(exc),
                    })

                if not loaded:
                    issues.append({
                        "code": f"{code}_NOT_FOUND",
                        "blocking": True,
                        "detail": str(path),
                    })

                if code == "RELEASE_TOKEN":
                    release_token = loaded
                elif code == "RUNTIME_POLICY":
                    policy = loaded
                else:
                    watchdog = loaded

            try:
                emergency = _load_json(emergency_stop_path)
            except Exception as exc:
                emergency = {}
                issues.append({
                    "code": "INVALID_EMERGENCY_STOP",
                    "blocking": True,
                    "detail": str(exc),
                })

        if release_token and (
            release_token.get("release_id") != release_id
            or release_token.get("engine_id") != engine_id
            or not bool(
                release_token.get("paper_production_release_ready", False)
            )
            or bool(release_token.get("live_trading_enabled", True))
            or bool(release_token.get("actual_submission_allowed", True))
            or bool(release_token.get("broker_network_allowed", True))
        ):
            issues.append({
                "code": "RELEASE_TOKEN_MISMATCH",
                "blocking": True,
                "detail": "release token violates local-only Paper contract",
            })

        emergency_stop_engaged = bool(emergency.get("engaged", False))
        if emergency_stop_engaged:
            issues.append({
                "code": "EMERGENCY_STOP_ENGAGED",
                "blocking": True,
                "detail": str(emergency.get("reason", "manual emergency stop")),
            })

        policy_ready = False
        session_id = ""
        interval_seconds = 0
        max_ticks = 0
        if policy:
            session_id = str(policy.get("session_id", "")).strip()
            interval_seconds = int(policy.get("interval_seconds", 0))
            max_ticks = int(policy.get("max_ticks_per_run", 0))
            checks = [
                ("SESSION_ID_MISSING", bool(session_id)),
                ("INVALID_RUNTIME_INTERVAL", interval_seconds >= 5),
                ("INVALID_TICK_LIMIT", 1 <= max_ticks <= 100),
                (
                    "CONTINUOUS_UNBOUNDED_LOOP_BLOCKED",
                    not bool(policy.get("unbounded_loop_enabled", True)),
                ),
                (
                    "ACTUAL_SUBMISSION_POLICY_BLOCKED",
                    not bool(policy.get("actual_submission_allowed", True)),
                ),
                (
                    "BROKER_NETWORK_POLICY_BLOCKED",
                    not bool(policy.get("broker_network_allowed", True)),
                ),
                (
                    "LIVE_TRADING_POLICY_BLOCKED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "runtime policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        watchdog_ready = False
        if watchdog:
            checks = [
                (
                    "WATCHDOG_HEARTBEAT_STALE",
                    int(watchdog.get("heartbeat_age_seconds", 999999))
                    <= int(watchdog.get("maximum_heartbeat_age_seconds", 120)),
                ),
                (
                    "WATCHDOG_PROCESS_DUPLICATE",
                    int(watchdog.get("runtime_process_count", 0)) <= 1,
                ),
                (
                    "WATCHDOG_DISK_LOW",
                    float(watchdog.get("disk_free_mb", 0))
                    >= float(watchdog.get("minimum_disk_free_mb", 1024)),
                ),
                (
                    "WATCHDOG_FILESYSTEM_UNAVAILABLE",
                    bool(watchdog.get("filesystem_writable", False)),
                ),
                (
                    "WATCHDOG_CLOCK_UNSYNCHRONIZED",
                    bool(watchdog.get("system_clock_synchronized", False)),
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "watchdog gate failed",
                    })
            watchdog_ready = all(passed for _, passed in checks)

        lock_acquired = False
        runtime_id = ""
        heartbeat_written = False
        tick_written = False
        runtime_token_written = False
        duplicate_runtime_token = False

        blocking = sum(1 for issue in issues if issue.get("blocking"))

        if (
            required
            and release_token
            and policy_ready
            and watchdog_ready
            and blocking == 0
        ):
            if runtime_lock_path.exists():
                try:
                    existing_lock = _load_json(runtime_lock_path)
                except Exception as exc:
                    existing_lock = {}
                    issues.append({
                        "code": "INVALID_RUNTIME_LOCK",
                        "blocking": True,
                        "detail": str(exc),
                    })

                if existing_lock and not bool(existing_lock.get("released", False)):
                    issues.append({
                        "code": "RUNTIME_LOCK_ACTIVE",
                        "blocking": True,
                        "detail": "another runtime process owns the lock",
                    })

            if not any(issue.get("blocking") for issue in issues):
                runtime_id = _runtime_id(release_id, session_id)
                _write_json(runtime_lock_path, {
                    "stage_range": "V142.01-V142.04",
                    "runtime_id": runtime_id,
                    "released": False,
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                })
                lock_acquired = True

        try:
            if lock_acquired:
                heartbeat_payload = {
                    "stage": "V142.03",
                    "runtime_id": runtime_id,
                    "session_id": session_id,
                    "status": "ALIVE",
                    "heartbeat_at": datetime.now(timezone.utc).isoformat(),
                    "interval_seconds": interval_seconds,
                    "tick_limit": max_ticks,
                }
                _write_json(heartbeat_path, heartbeat_payload)
                heartbeat_written = True

                tick_payload = {
                    "stage": "V142.02",
                    "runtime_id": runtime_id,
                    "session_id": session_id,
                    "tick_number": 1,
                    "tick_limit": max_ticks,
                    "action": "LOCAL_PIPELINE_STATUS_CHECK",
                    "broker_network_used": False,
                    "actual_submission_attempted": False,
                    "live_submission_attempted": False,
                    "emergency_stop_engaged": False,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
                _write_json(tick_result_path, tick_payload)
                tick_written = True

                token_payload = {
                    "stage": "V142.01",
                    "runtime_id": runtime_id,
                    "release_id": release_id,
                    "engine_id": engine_id,
                    "session_id": session_id,
                    "autonomous_paper_runtime_ready": True,
                    "continuous_loop_enabled": False,
                    "watchdog_ready": True,
                    "emergency_stop_ready": True,
                    "live_trading_enabled": False,
                    "actual_submission_allowed": False,
                    "broker_network_allowed": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }

                if runtime_token_path.exists():
                    existing = _load_json(runtime_token_path)
                    if existing.get("runtime_id") == runtime_id:
                        duplicate_runtime_token = True
                    else:
                        issues.append({
                            "code": "RUNTIME_TOKEN_CONFLICT",
                            "blocking": True,
                            "detail": "existing runtime token belongs to another session",
                        })
                else:
                    _write_json(runtime_token_path, token_payload)
                    runtime_token_written = True
        finally:
            if lock_acquired:
                _write_json(runtime_lock_path, {
                    "stage_range": "V142.01-V142.04",
                    "runtime_id": runtime_id,
                    "released": True,
                    "released_at": datetime.now(timezone.utc).isoformat(),
                })

        blocking = sum(1 for issue in issues if issue.get("blocking"))
        safe_mode = blocking > 0
        runtime_ready = bool(
            required
            and policy_ready
            and watchdog_ready
            and heartbeat_written
            and tick_written
            and (runtime_token_written or duplicate_runtime_token)
            and not safe_mode
        )

        if emergency_stop_engaged:
            state, status = "AUTONOMOUS_RUNTIME_EMERGENCY_STOP", "BLOCKED"
        elif safe_mode:
            state, status = "AUTONOMOUS_RUNTIME_SAFE_MODE", "BLOCKED"
        elif runtime_ready:
            state, status = "AUTONOMOUS_PAPER_RUNTIME_READY", "PASS"
        else:
            state, status = "WAIT_PAPER_PRODUCTION_RELEASE", "PASS"

        result = {
            "stage_range": "V142.01-V142.04",
            "implementation_type": "ULTRA_FAST_AUTONOMOUS_PAPER_RUNTIME",
            "status": status,
            "state": state,
            "release_id": release_id,
            "engine_id": engine_id,
            "runtime_id": runtime_id,
            "session_id": session_id,
            "runtime_policy_ready": policy_ready,
            "watchdog_ready": watchdog_ready,
            "emergency_stop_engaged": emergency_stop_engaged,
            "runtime_lock_verified": bool(lock_acquired or not required),
            "heartbeat_written": heartbeat_written,
            "runtime_tick_written": tick_written,
            "runtime_token_written": runtime_token_written,
            "duplicate_runtime_token": duplicate_runtime_token,
            "autonomous_paper_runtime_ready": runtime_ready,
            "continuous_loop_enabled": False,
            "safe_mode_engaged": safe_mode,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "V142_05_TO_V142_08_SCHEDULED_RUNTIME"
                if runtime_ready
                else "V142_01_TO_V142_04_WAIT_RELEASE"
            ),
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "live_trading_enabled": False,
            "validation_mode": "LOCAL_SINGLE_TICK_RUNTIME_ONLY",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "result_path": str(result_path.resolve()),
        }
        _write_json(result_path, result)
        return result
