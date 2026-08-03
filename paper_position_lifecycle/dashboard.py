from __future__ import annotations
from pathlib import Path
from paper_position_lifecycle.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v95_33_to_v95_64/actual/paper_position_lifecycle_result.json"
    )
    return {
        "position_lifecycle_state": result.get("state", "NOT_AVAILABLE"),
        "lifecycle_date": result.get("lifecycle_date"),
        "position_decisions": result.get("position_decisions", []),
        "close_records": result.get("close_records", []),
        "open_position_count": result.get("open_position_count", 0),
        "closed_position_count": result.get("closed_position_count", 0),
        "total_realized_pnl": result.get("total_realized_pnl", 0.0),
        "actual_orders_submitted": 0,
        "paper_only": True,
    }
