from __future__ import annotations
from pathlib import Path
from portfolio_rebalance.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v99_33_to_v99_64/actual/"
        "portfolio_rebalance_result.json"
    )
    return {
        "rebalance_state": result.get("state", "NOT_AVAILABLE"),
        "rebalance_id": result.get("rebalance_id"),
        "weight_comparison": result.get("weight_comparison", []),
        "actionable_intent_count": result.get("actionable_intent_count", 0),
        "duplicate_intent_count": result.get("duplicate_intent_count", 0),
        "risk": result.get("risk", {}),
        "execution_authorized": False,
        "manual_approval_required": True,
        "paper_only": True,
    }
