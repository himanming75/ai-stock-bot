from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from paper_position_lifecycle.engine import evaluate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--lifecycle-date",default="")
    args=parser.parse_args()
    result=evaluate(ROOT,args.lifecycle_date)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "lifecycle_date":result.get("lifecycle_date"),
        "open_position_count":result.get("open_position_count",0),
        "closed_position_count":result.get("closed_position_count",0),
        "total_realized_pnl":result.get("total_realized_pnl"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={(ROOT/'release/v95_33_to_v95_64/actual/paper_position_lifecycle_result.json').resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
