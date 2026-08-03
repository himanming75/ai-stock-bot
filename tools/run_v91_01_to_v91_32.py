from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from strategy_lab.engine import run_lab
from strategy_lab.io import write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="")
    args=parser.parse_args()
    result=run_lab(ROOT,args.input)
    out=ROOT/"release/v91_01_to_v91_32/actual/ultimate_strategy_lab_result.json"
    write_json(out,result)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "registered_strategy_count":result.get("registered_strategy_count",0),
        "executed_strategy_count":result.get("executed_strategy_count",0),
        "approved_strategy_count":result.get("approved_strategy_count",0),
        "champion":result.get("champion",{}).get("strategy_name") if result.get("champion") else None,
        "top_candidate":result.get("top_candidate",{}).get("strategy_name") if result.get("top_candidate") else None,
        "bar_count":result.get("bar_count"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
