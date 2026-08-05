from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _parse(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def evaluate_watchdog(
    root: Path,
    *,
    maximum_heartbeat_age_seconds: int = 180,
) -> dict[str, Any]:
    heartbeat_path = (
        root / "release/p4_autonomous_paper_runtime/actual/"
               "heartbeat.json"
    )
    lock_path = (
        root / "release/p4_autonomous_paper_runtime/actual/"
               "runtime.lock.json"
    )
    checkpoint_path = (
        root / "release/p4_autonomous_paper_runtime/actual/"
               "runtime_checkpoint.json"
    )

    heartbeat = {}
    if heartbeat_path.exists():
        heartbeat = json.loads(
            heartbeat_path.read_text(encoding="utf-8-sig")
        )

    observed = _parse(heartbeat.get("observed_at"))
    now = datetime.now(timezone.utc)
    age = (
        (now - observed).total_seconds()
        if observed is not None else None
    )
    runtime_expected = lock_path.exists()

    checks = {
        "checkpoint_present": checkpoint_path.exists(),
        "heartbeat_present_when_runtime_expected": (
            not runtime_expected or heartbeat_path.exists()
        ),
        "heartbeat_fresh_when_runtime_expected": (
            not runtime_expected
            or (age is not None and age <= maximum_heartbeat_age_seconds)
        ),
        "live_network_disabled": True,
        "live_write_disabled": True,
    }
    failed = [key for key, passed in checks.items() if not passed]

    recovery_actions = []
    if runtime_expected and (
        age is None or age > maximum_heartbeat_age_seconds
    ):
        recovery_actions.extend([
            "HALT_NEW_ORDERS",
            "PRESERVE_RUNTIME_LOCK_AND_CHECKPOINT",
            "REQUIRE_OPERATOR_RESTART_REVIEW",
        ])
    if not checkpoint_path.exists():
        recovery_actions.append("REBUILD_CHECKPOINT_BEFORE_RUNTIME")
    if not recovery_actions:
        recovery_actions.append("NO_RECOVERY_REQUIRED")

    return {
        "stage": "O2_WATCHDOG",
        "status": "PASS" if not failed else "BLOCKED",
        "checks": checks,
        "failed": failed,
        "runtime_expected": runtime_expected,
        "heartbeat_age_seconds": age,
        "maximum_heartbeat_age_seconds": (
            maximum_heartbeat_age_seconds
        ),
        "recovery_actions": recovery_actions,
        "automatic_broker_restart_enabled": False,
        "automatic_order_replay_enabled": False,
        "actual_live_orders_submitted": 0,
    }
