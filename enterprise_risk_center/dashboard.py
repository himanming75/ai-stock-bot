from __future__ import annotations
from pathlib import Path
from enterprise_risk_center.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v92_33_to_v92_64/actual/"
        "enterprise_risk_center_result.json"
    )
    return {
        "risk_center_state": result.get("state", "NOT_AVAILABLE"),
        "risk_approved": result.get("risk_approved", False),
        "risk_metrics": result.get("risk_metrics", {}),
        "guards": result.get("guards", {}),
        "failed_risk_checks": result.get("failed_risk_checks", []),
        "stress_scenarios": result.get("stress_scenarios", []),
        "monte_carlo": result.get("monte_carlo", {}),
        "paper_only": True,
    }
