from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from autonomous_paper_operations.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    report=result.get("operations_report",{})
    champion=(result.get("tournament",{}).get("champion") or {})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "operations_id":result.get("operations_id"),
        "champion_strategy":champion.get("strategy_id"),
        "champion_score":champion.get("tournament_score"),
        "session_count":report.get("session_count"),
        "completed_count":report.get("completed_count"),
        "failed_count":report.get("failed_count"),
        "starting_equity":report.get("starting_equity"),
        "ending_equity":report.get("ending_equity"),
        "cumulative_pnl":report.get("cumulative_pnl"),
        "cumulative_return_pct":report.get("cumulative_return_pct"),
        "automatic_restart_enabled":result.get("automatic_restart_enabled"),
        "daily_backup_enabled":result.get("daily_backup_enabled"),
        "windows_task_installed":result.get("windows_task_installed"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v109_01_to_v110_64/actual/"
                "autonomous_paper_operations_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
