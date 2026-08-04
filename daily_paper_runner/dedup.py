from __future__ import annotations
from typing import Any

FINAL_STATES = {
    "DAILY_PAPER_TRADING_RUN_COMPLETED",
    "DAILY_PAPER_TRADING_RUN_NO_ACTION",
}

def detect_duplicate(
    run_key: str,
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    matches = [
        row for row in ledger_rows
        if row.get("run_key") == run_key
        and row.get("state") in FINAL_STATES
    ]
    return {
        "duplicate": bool(matches),
        "match_count": len(matches),
        "previous_run_id": matches[-1].get("run_id") if matches else None,
        "previous_state": matches[-1].get("state") if matches else None,
    }
