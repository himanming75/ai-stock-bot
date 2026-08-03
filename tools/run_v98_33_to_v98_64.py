from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from backtest_batch.engine import evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--no-resume",action="store_true")
    args=parser.parse_args()
    result=evaluate(ROOT,resume=not args.no_resume)
    champion=result.get("champion") or {}
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "batch_id":result.get("batch_id"),
        "job_count":result.get("job_count",0),
        "completed_count":result.get("completed_count",0),
        "failed_count":result.get("failed_count",0),
        "regression_pass_count":result.get("regression_pass_count",0),
        "regression_fail_count":result.get("regression_fail_count",0),
        "champion_strategy":champion.get("strategy_id"),
        "champion_score":champion.get("average_regression_score"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={(ROOT/'release/v98_33_to_v98_64/actual/backtest_batch_result.json').resolve()}")
    return 0
if __name__=="__main__": raise SystemExit(main())
