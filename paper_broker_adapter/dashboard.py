from __future__ import annotations
from pathlib import Path
from paper_broker_adapter.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v97_01_to_v97_32/actual/"
        "paper_broker_adapter_result.json"
    )
    return {
        "paper_broker_adapter_state": result.get(
            "state", "NOT_AVAILABLE"
        ),
        "adapter_name": result.get("adapter_name"),
        "adapter_capabilities": result.get(
            "adapter_capabilities", {}
        ),
        "adapter_health": result.get("adapter_health", {}),
        "safe_api_boundary": result.get("safe_api_boundary", {}),
        "account_snapshot": result.get("account_snapshot", {}),
        "positions_snapshot": result.get("positions_snapshot", []),
        "actual_orders_submitted": 0,
        "paper_only": True,
    }
