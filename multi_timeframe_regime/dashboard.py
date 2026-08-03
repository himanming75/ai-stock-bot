from __future__ import annotations
from pathlib import Path
from multi_timeframe_regime.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v93_33_to_v93_64/actual/multi_timeframe_regime_result.json"
    )
    return {
        "multi_timeframe_state": result.get("state", "NOT_AVAILABLE"),
        "frames": result.get("frames", []),
        "consensus": result.get("consensus", {}),
        "recommended_strategies": result.get("recommended_strategies", []),
        "effective_position_multiplier": result.get("effective_position_multiplier", 0.0),
        "failed_checks": result.get("failed_checks", []),
        "paper_only": True,
    }
