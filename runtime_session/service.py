from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from configuration_profiles.loader import load_profile
from runtime_configuration.binding import bind_profile_to_runtime

from .gates import evaluate_session_gate
from .io import append_jsonl, read_json, write_json
from .lock import SessionLock
from .models import SessionPolicy
from .paths import (
    active_session_path,
    checkpoint_path,
    heartbeat_path,
    lock_path,
    session_ledger_path,
    stop_marker_path,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot_hash(value: dict[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_preview_session(
    root: Path,
    profile_path: Path,
    *,
    release_lock: bool = True,
) -> dict[str, Any]:
    profile, validation = load_profile(profile_path)
    if not validation["valid"]:
        raise ValueError("INVALID_PROFILE:" + ",".join(validation["failed"]))

    runtime = bind_profile_to_runtime(profile)
    policy = SessionPolicy()
    policy_result = policy.validate()
    gate = evaluate_session_gate(root, runtime.broker_mode)

    session_id = f"r6-{uuid.uuid4().hex}"
    lock = SessionLock(lock_path(root))
    lock.acquire(session_id)

    try:
        runtime_snapshot = runtime.as_json()
        session = {
            "stage": "R6",
            "session_id": session_id,
            "profile_name": runtime.profile_name,
            "broker_mode": runtime.broker_mode,
            "horizon": runtime.horizon,
            "state": "PREVIEW_SESSION_ACTIVE",
            "started_at": _now(),
            "runtime_snapshot": runtime_snapshot,
            "runtime_snapshot_hash": _snapshot_hash(runtime_snapshot),
            "policy": policy_result,
            "gate": gate,
            "broker_network_enabled": False,
            "broker_write_enabled": False,
            "automatic_order_submission_enabled": False,
            "automatic_order_replay_enabled": False,
            "automatic_broker_restart_enabled": False,
            "actual_paper_orders_submitted": 0,
            "actual_live_orders_submitted": 0,
        }
        write_json(active_session_path(root), session)
        write_json(heartbeat_path(root), {
            "session_id": session_id,
            "state": "HEALTHY",
            "observed_at": _now(),
            "cycle_number": 0,
        })
        write_json(checkpoint_path(root), {
            "session_id": session_id,
            "profile_name": runtime.profile_name,
            "state": "SESSION_CREATED",
            "cycle_number": 0,
            "updated_at": _now(),
            "automatic_order_replay_enabled": False,
        })
        append_jsonl(session_ledger_path(root), {
            "record_type": "SESSION_CREATED",
            "session_id": session_id,
            "profile_name": runtime.profile_name,
            "observed_at": _now(),
            "broker_network_used": False,
            "order_submission_attempted": False,
        })

        session["state"] = "PREVIEW_SESSION_COMPLETE"
        session["ended_at"] = _now()
        write_json(active_session_path(root), session)
        append_jsonl(session_ledger_path(root), {
            "record_type": "SESSION_COMPLETED",
            "session_id": session_id,
            "observed_at": _now(),
            "broker_network_used": False,
            "order_submission_attempted": False,
        })
        return session
    finally:
        if release_lock:
            lock.release(session_id)


def request_stop(root: Path, reason: str) -> dict[str, Any]:
    active = read_json(active_session_path(root))
    result = {
        "stage": "R6_STOP_REQUEST",
        "requested_at": _now(),
        "reason": reason,
        "session_id": active.get("session_id", ""),
        "new_order_submission_allowed": False,
        "automatic_process_termination_enabled": False,
        "automatic_order_replay_enabled": False,
        "operator_review_required": True,
    }
    write_json(stop_marker_path(root), result)
    return result


def resume_preview(root: Path) -> dict[str, Any]:
    checkpoint = read_json(checkpoint_path(root))
    heartbeat = read_json(heartbeat_path(root))
    checks = {
        "checkpoint_present": bool(checkpoint),
        "heartbeat_present": bool(heartbeat),
        "session_id_matches": (
            bool(checkpoint)
            and bool(heartbeat)
            and checkpoint.get("session_id") == heartbeat.get("session_id")
        ),
        "automatic_order_replay_off": (
            checkpoint.get("automatic_order_replay_enabled") is False
        ),
    }
    return {
        "stage": "R6_RESUME_PREVIEW",
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "safe_to_auto_resume": False,
        "automatic_order_replay_enabled": False,
        "operator_review_required": True,
        "required_action": "OPERATOR_REVIEW_THEN_NEW_SESSION",
    }
