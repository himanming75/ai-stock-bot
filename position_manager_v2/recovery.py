from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from position_manager_v2.io import load_json, write_json

def build(root: Path) -> dict:
    snapshot = load_json(root / "release/v236_01_to_v240_64/actual/position_snapshot.json")
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_present": bool(snapshot),
        "snapshot": snapshot,
        "steps": [
            "ENABLE_EMERGENCY_STOP",
            "READ_LOCAL_POSITION_SNAPSHOT",
            "READ_BROKER_POSITIONS",
            "COMPARE_QUANTITIES",
            "COMPARE_AVERAGE_COST",
            "RECALCULATE_EXPOSURE",
            "BLOCK_ON_CONFLICT",
            "RESUME_MONITORING_ONLY",
        ],
        "automatic_submission_allowed": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v236_01_to_v240_64/actual/position_recovery_plan.json", result)
    return result
