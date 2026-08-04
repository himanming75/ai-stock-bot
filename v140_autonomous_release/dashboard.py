from pathlib import Path
from v140_autonomous_release.io import load_json

def build_dashboard_payload(root:Path)->dict:
    r=load_json(root/"release/v140_final/actual/v140_final_release_result.json")
    return {
        "state":r.get("state"),
        "development_complete":r.get("development_complete"),
        "paper_trading_ready":r.get("paper_trading_ready"),
        "autonomous_paper_orchestrator_ready":r.get("autonomous_paper_orchestrator_ready"),
        "live_trading_ready":r.get("live_trading_ready"),
        "next_phase":r.get("next_phase"),
        "actual_live_orders_submitted":0,
    }
