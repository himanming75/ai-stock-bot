from __future__ import annotations
from pathlib import Path
from final_release.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v105_33_to_v105_64/actual/"
        "production_readiness_final_release_result.json"
    )
    return {
        "state": result.get("state", "NOT_AVAILABLE"),
        "release_id": result.get("release_id"),
        "release_version": result.get("release_version"),
        "project_complete": result.get("project_complete"),
        "production_release_created": result.get(
            "production_release_created"
        ),
        "readiness": result.get("readiness", {}),
        "integrity": result.get("integrity", {}),
        "acceptance": result.get("acceptance", {}),
        "bundle": result.get("bundle", {}),
        "paper_trading_ready": result.get("paper_trading_ready"),
        "live_trading_ready": False,
        "execution_authorized": False,
        "paper_only": True,
    }
