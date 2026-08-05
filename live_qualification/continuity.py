from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
from typing import Any


def _parse(value: str):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def audit_heartbeat_continuity(
    ledger_path: Path,
    *,
    maximum_gap_seconds: int,
) -> dict[str, Any]:
    if not ledger_path.exists():
        return {
            "sample_count": 0,
            "maximum_gap_seconds_observed": 0,
            "passed": True,
        }

    timestamps = []
    for line in ledger_path.read_text(
        encoding="utf-8-sig",
        errors="replace",
    ).splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            observed_at = value.get("observed_at")
            if observed_at:
                timestamps.append(_parse(observed_at))
        except Exception:
            continue

    timestamps.sort()
    gaps = [
        (timestamps[i] - timestamps[i - 1]).total_seconds()
        for i in range(1, len(timestamps))
    ]
    maximum_gap = max(gaps) if gaps else 0
    return {
        "sample_count": len(timestamps),
        "maximum_gap_seconds_observed": maximum_gap,
        "maximum_gap_seconds_allowed": maximum_gap_seconds,
        "passed": maximum_gap <= maximum_gap_seconds,
    }


def audit_checkpoint_continuity(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "checkpoint_present": False,
            "passed": False,
        }
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    checks = {
        "checkpoint_present": True,
        "runtime_id_present": bool(value.get("runtime_id")),
        "cycle_id_present": bool(value.get("cycle_id")),
        "cycle_number_positive": int(value.get("cycle_number", 0)) > 0,
        "state_complete": value.get("state") == "L5_CYCLE_COMPLETE",
        "auto_replay_off": (
            value.get("automatic_order_replay_enabled") is False
        ),
    }
    return {
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "passed": all(checks.values()),
    }
