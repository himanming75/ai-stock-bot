from __future__ import annotations
from pathlib import Path
from paper_broker_read_model.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v97_33_to_v97_64/actual/"
        "paper_broker_snapshot_reconciliation_result.json"
    )
    return {
        "paper_broker_read_model_state": result.get(
            "state", "NOT_AVAILABLE"
        ),
        "source_adapter_name": result.get("source_adapter_name"),
        "account_reconciliation": result.get(
            "account_reconciliation", {}
        ),
        "position_reconciliation": result.get(
            "position_reconciliation", {}
        ),
        "snapshot_freshness": result.get("snapshot_freshness", {}),
        "integrity": result.get("integrity", {}),
        "actual_orders_submitted": 0,
        "paper_only": True,
    }
