from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from multi_day_scheduler.engine import evaluate

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--start-date",default=None)
    parser.add_argument("--session-count",type=int,default=None)
    args=parser.parse_args()

    result=evaluate(
        ROOT,
        start_date=args.start_date,
        session_count=args.session_count,
    )
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "scheduler_id":result.get("scheduler_id"),
        "source_cycle_id":result.get("source_cycle_id"),
        "scheduler_action":result.get("scheduler_action"),
        "requested_start_date":result.get("requested_start_date"),
        "requested_session_count":result.get("requested_session_count"),
        "start_date_is_trading_day":result.get("start_date_is_trading_day"),
        "next_trading_day":result.get("next_trading_day"),
        "scheduled_trading_days":result.get("scheduled_trading_days"),
        "session_count":result.get("queue_summary",{}).get("session_count"),
        "queued_count":result.get("queue_summary",{}).get("queued_count"),
        "duplicate_count":result.get("duplicate_analysis",{}).get("duplicate_count"),
        "checkpoint_generation":result.get("checkpoint",{}).get("generation"),
        "resume_supported":result.get("resume_supported"),
        "manual_approval_required":result.get("manual_approval_required"),
        "execution_authorized":result.get("execution_authorized"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v103_33_to_v103_64/actual/"
                "multi_day_scheduler_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
