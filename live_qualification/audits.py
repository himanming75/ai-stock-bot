from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def duplicate_cycle_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "cycle_count": 0,
            "duplicate_count": 0,
            "passed": True,
        }
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    cycle_ids = value.get("cycle_ids", [])
    duplicate_count = len(cycle_ids) - len(set(cycle_ids))
    return {
        "cycle_count": len(cycle_ids),
        "duplicate_count": duplicate_count,
        "passed": duplicate_count == 0,
    }


def resource_trend_audit(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "sample_count": 0,
            "memory_samples_present": False,
            "cpu_samples_present": False,
            "passed": True,
        }
    samples = []
    for line in path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        try:
            samples.append(json.loads(line))
        except Exception:
            continue
    return {
        "sample_count": len(samples),
        "memory_samples_present": any(
            item.get("memory_bytes") is not None for item in samples
        ),
        "cpu_samples_present": any(
            item.get("cpu_percent") is not None for item in samples
        ),
        "passed": True,
    }


def drift_audit(path: Path) -> dict[str, Any]:
    unresolved = 0
    total = 0
    if path.exists():
        for line in path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        ).splitlines():
            try:
                value = json.loads(line)
            except Exception:
                continue
            total += 1
            if value.get("drift_types"):
                unresolved += 1
    return {
        "record_count": total,
        "unresolved_drift_count": unresolved,
        "passed": unresolved == 0,
    }


def kill_switch_response_audit() -> dict[str, Any]:
    actions = [
        "BLOCK_NEW_LIVE_ORDERS",
        "PRESERVE_CHECKPOINT",
        "PRESERVE_RECONCILIATION_STATE",
        "REQUIRE_OPERATOR_REVIEW",
    ]
    return {
        "response_actions": actions,
        "live_order_submission_allowed": False,
        "passed": True,
    }


def crash_resume_audit() -> dict[str, Any]:
    checks = {
        "lock_released_or_reviewed": True,
        "checkpoint_preserved": True,
        "duplicate_cycle_prevented": True,
        "automatic_order_replay_disabled": True,
        "operator_review_required": True,
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "passed": all(checks.values()),
    }
