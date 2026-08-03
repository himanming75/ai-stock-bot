from __future__ import annotations
from pathlib import Path
from market_regime_engine.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v93_01_to_v93_32/actual/market_regime_result.json"
    )
    return {
        "market_regime_state": result.get("state", "NOT_AVAILABLE"),
        "regime": result.get("regime", {}),
        "features": result.get("features", {}),
        "recommended_strategies": result.get("recommended_strategies", []),
        "effective_position_multiplier": result.get(
            "effective_position_multiplier", 0.0
        ),
        "failed_checks": result.get("failed_checks", []),
        "paper_only": True,
    }
