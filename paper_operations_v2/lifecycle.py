from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from paper_operations_v2.io import append_jsonl, write_json

ALLOWED = {
    "PLANNED",
    "SUBMISSION_BLOCKED",
    "SUBMITTED",
    "ACCEPTED",
    "PARTIALLY_FILLED",
    "FILLED",
    "CANCELED",
    "REJECTED",
    "EXPIRED",
    "RECONCILED",
}

def record(root: Path, cycle_id: str, order_id: str, state: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    if state not in ALLOWED:
        raise ValueError(f"Unsupported lifecycle state: {state}")
    row = {
        "cycle_id": cycle_id,
        "order_id": order_id,
        "state": state,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
        "actual_live_orders_submitted": 0,
    }
    actual = root / "release/v221_01_to_v225_64/actual"
    append_jsonl(actual / "paper_order_lifecycle_ledger.jsonl", row)
    write_json(actual / "last_paper_order_lifecycle.json", row)
    return row
