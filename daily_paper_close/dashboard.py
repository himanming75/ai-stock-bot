from __future__ import annotations
from pathlib import Path
from daily_paper_close.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v96_33_to_v96_64/actual/"
        "daily_paper_close_result.json"
    )
    return {
        "daily_close_state": result.get("state", "NOT_AVAILABLE"),
        "close_date": result.get("close_date"),
        "daily_metrics": result.get("daily_metrics", {}),
        "fill_summary": result.get("fill_summary", {}),
        "position_summary": result.get("position_summary", {}),
        "risk_summary": result.get("risk_summary", {}),
        "account_summary": result.get("account_summary", {}),
        "close_gates": result.get("close_gates", {}),
        "paper_only": True,
    }
