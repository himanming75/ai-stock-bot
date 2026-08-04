from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_trading.io import write_json

def build(root: Path, result: dict) -> dict:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_id": result["session_id"],
        "cycle_count": result["cycle_count"],
        "paper_orders_submitted": result["actual_paper_orders_submitted"],
        "live_orders_submitted": 0,
        "market_open": result["market_open"],
        "final_state": result["state"],
        "blocking_reasons": result["blocking_reasons"],
    }
    write_json(
        root / "release/v256_01_to_v260_64/actual/autonomous_paper_daily_report.json",
        report,
    )
    return report
