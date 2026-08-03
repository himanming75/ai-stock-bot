from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from parameter_optimizer.engine import optimize
from parameter_optimizer.io import write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",default="")
    args=parser.parse_args()

    result=optimize(ROOT,args.input)
    out=ROOT/"release/v91_33_to_v91_64/actual/parameter_optimization_result.json"
    write_json(out,result)

    stable=result.get("best_stable_candidate")
    candidate=result.get("best_candidate")
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "bar_count":result.get("bar_count"),
        "evaluated_combination_count":result.get("evaluated_combination_count",0),
        "stable_combination_count":result.get("stable_combination_count",0),
        "best_stable_strategy":stable.get("strategy_id") if stable else None,
        "best_stable_parameters":stable.get("parameters") if stable else None,
        "best_candidate_strategy":candidate.get("strategy_id") if candidate else None,
        "best_candidate_parameters":candidate.get("parameters") if candidate else None,
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
