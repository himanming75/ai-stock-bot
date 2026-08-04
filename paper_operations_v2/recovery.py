from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paper_operations_v2.io import write_json
from paper_operations_v2.state import load_checkpoint

def build(root: Path) -> dict[str, Any]:
    checkpoint = load_checkpoint(root)
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint_present": bool(checkpoint),
        "last_checkpoint": checkpoint,
        "steps": [
            "ENABLE_EMERGENCY_STOP",
            "READ_LAST_CHECKPOINT",
            "READ_PAPER_OPEN_ORDERS",
            "READ_PAPER_POSITIONS",
            "RECONCILE_LOCAL_AND_BROKER_STATE",
            "BLOCK_NEW_ORDER_ON_CONFLICT",
            "RESUME_FROM_SAFE_STEP",
        ],
        "automatic_live_resume_allowed": False,
        "broker_write_enabled": False,
        "actual_live_orders_submitted": 0,
    }
    write_json(root / "release/v221_01_to_v225_64/actual/paper_recovery_plan.json", result)
    return result
