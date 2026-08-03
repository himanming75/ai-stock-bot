from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from automated_backtest.engine import evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    result=evaluate(ROOT,force=args.force)
    aggregation=result.get("aggregation",{})
    top=aggregation.get("top_result") or {}
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "run_id":result.get("run_id"),
        "strategy_count":result.get("strategy_count",0),
        "dataset_count":result.get("dataset_count",0),
        "window_count":result.get("window_count",0),
        "job_count":result.get("job_count",0),
        "completed_count":aggregation.get("completed_count",0),
        "skipped_count":aggregation.get("skipped_count",0),
        "failed_count":aggregation.get("failed_count",0),
        "cache_hit_count":result.get("cache_hit_count",0),
        "top_strategy":top.get("strategy_id"),
        "top_symbol":top.get("symbol"),
        "top_return_pct":top.get("total_return_pct"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v98_01_to_v98_32/actual/"
                "automated_backtest_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
