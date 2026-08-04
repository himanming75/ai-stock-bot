from pathlib import Path
from v120_final_release.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    r=load_json(root/"release/v120_final/actual/v120_final_release_result.json")
    return {
        "state":r.get("state"),
        "release_id":r.get("release_id"),
        "development_complete":r.get("development_complete"),
        "paper_trading_ready":r.get("paper_trading_ready"),
        "live_trading_ready":False,
        "integration":r.get("integration",{}),
        "safety":r.get("safety",{}),
        "acceptance":r.get("acceptance",{}),
        "bundle":r.get("bundle",{}),
        "actual_orders_submitted":0,
    }
