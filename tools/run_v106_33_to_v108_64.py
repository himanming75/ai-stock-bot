from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from fast_track_paper.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    close=result.get("daily_close",{})
    analytics=result.get("analytics",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "cycle_id":result.get("cycle_id"),
        "session_date":result.get("session_date"),
        "paper_order_count":result.get("paper_order_count"),
        "filled_count":result.get("filled_count"),
        "partial_fill_count":result.get("partial_fill_count"),
        "not_filled_count":result.get("not_filled_count"),
        "exit_count":result.get("exit_count"),
        "ending_cash":close.get("ending_cash"),
        "ending_equity":close.get("ending_equity"),
        "realized_pnl":close.get("realized_pnl"),
        "unrealized_pnl":close.get("unrealized_pnl"),
        "total_pnl":close.get("total_pnl"),
        "daily_return_pct":analytics.get("daily_return_pct"),
        "cumulative_return_pct":analytics.get("cumulative_return_pct"),
        "win_rate_pct":analytics.get("win_rate_pct"),
        "annualized_sharpe":analytics.get("annualized_sharpe"),
        "maximum_drawdown_pct":analytics.get("maximum_drawdown_pct"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v106_33_to_v108_64/actual/"
                "fast_track_paper_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
