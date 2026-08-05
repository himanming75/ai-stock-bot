from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def scheduler_status(root: Path) -> dict[str, Any]:
    policy_path = (
        root / "release/p4_autonomous_paper_runtime/config/"
               "p4_runtime_policy.json"
    )
    checkpoint_path = (
        root / "release/p4_autonomous_paper_runtime/actual/"
               "runtime_checkpoint.json"
    )

    policy = {}
    checkpoint = {}
    if policy_path.exists():
        policy = json.loads(
            policy_path.read_text(encoding="utf-8-sig")
        )
    if checkpoint_path.exists():
        checkpoint = json.loads(
            checkpoint_path.read_text(encoding="utf-8-sig")
        )

    checks = {
        "policy_present": bool(policy),
        "cycle_interval_positive": (
            int(policy.get("cycle_interval_seconds", 0)) > 0
        ),
        "maximum_cycles_positive": (
            int(policy.get("maximum_cycles_per_session", 0)) > 0
        ),
        "market_open_required": (
            policy.get("require_market_open") is True
        ),
        "fail_closed": policy.get("fail_closed") is True,
    }

    return {
        "stage": "O2_SCHEDULER_MONITOR",
        "status": (
            "PASS" if all(checks.values()) else "BLOCKED"
        ),
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "policy": policy,
        "checkpoint": checkpoint,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "actual_live_orders_submitted": 0,
    }
