from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from exit_manager_v2.io import load_json, write_json

def build(root: Path) -> dict:
    snapshot = load_json(root / "release/v241_01_to_v245_64/actual/exit_candidate_snapshot.json")
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_present": bool(snapshot),
        "snapshot": snapshot,
        "steps": [
            "ENABLE_EMERGENCY_STOP",
            "READ_POSITION_SNAPSHOT",
            "READ_EXIT_CANDIDATE_SNAPSHOT",
            "RECALCULATE_ACTIVE_STOPS",
            "RECHECK_BROKER_POSITION",
            "BLOCK_DUPLICATE_EXIT",
            "RESUME_MONITORING_ONLY",
        ],
        "automatic_submission_allowed": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v241_01_to_v245_64/actual/exit_recovery_plan.json", result)
    return result
