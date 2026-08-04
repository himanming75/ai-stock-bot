from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paper_operations_v2.io import load_json, write_json

STEPS = [
    "PRE_MARKET_CHECK",
    "SIGNAL_COLLECTION",
    "RISK_GATE",
    "PAPER_ORDER_PLAN",
    "PAPER_ORDER_SUBMISSION",
    "FILL_MONITOR",
    "POSITION_RECONCILIATION",
    "END_OF_DAY_REPORT",
    "CHECKPOINT_COMPLETE",
]

def checkpoint_path(root: Path) -> Path:
    return root / "release/v221_01_to_v225_64/actual/paper_operations_checkpoint.json"

def load_checkpoint(root: Path) -> dict[str, Any]:
    return load_json(checkpoint_path(root))

def save_checkpoint(root: Path, cycle_id: str, step: str, status: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    value = {
        "cycle_id": cycle_id,
        "step": step,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
        "actual_live_orders_submitted": 0,
    }
    write_json(checkpoint_path(root), value)
    return value
