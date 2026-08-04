from __future__ import annotations
from typing import Any

def build_operations_report(
    sessions: list[dict[str, Any]],
    tournament: dict[str, Any],
    total_starting_equity: float,
) -> dict[str, Any]:
    completed=[row for row in sessions if row.get("state")=="COMPLETED"]
    failed=[row for row in sessions if row.get("state")=="FAILED"]
    final_equity=(
        float(completed[-1].get("ending_equity",total_starting_equity))
        if completed else total_starting_equity
    )
    return {
        "session_count":len(sessions),
        "completed_count":len(completed),
        "failed_count":len(failed),
        "starting_equity":round(total_starting_equity,2),
        "ending_equity":round(final_equity,2),
        "cumulative_pnl":round(final_equity-total_starting_equity,2),
        "cumulative_return_pct":round(
            (final_equity/total_starting_equity-1)*100
            if total_starting_equity else 0.0,
            6,
        ),
        "champion_strategy":(
            (tournament.get("champion") or {}).get("strategy_id")
        ),
        "all_sessions_completed":len(failed)==0 and len(completed)==len(sessions),
    }
