from __future__ import annotations
from pathlib import Path
from adaptive_rebalance.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v101_33_to_v101_64/actual/"
        "adaptive_rebalance_optimization_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "adaptive_rebalance_id": result.get("adaptive_rebalance_id"),
        "regime": result.get("regime", {}),
        "regime_multiplier": result.get("regime_multiplier"),
        "optimized_adjustments": result.get("optimized_adjustments", []),
        "stability": result.get("stability", {}),
        "optimization_gate": result.get("optimization_gate", {}),
        "execution_authorized": False,
        "paper_only": True,
    }
