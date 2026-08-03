from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from meta_strategy_engine.engine import evaluate
from meta_strategy_engine.io import write_json

def main():
    result=evaluate(ROOT)
    out=ROOT/"release/v94_01_to_v94_32/actual/meta_strategy_result.json"
    write_json(out,result)
    selected=result.get("selected_strategy") or {}
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "paper_decision":result.get("paper_decision"),
        "selected_strategy_id":selected.get("strategy_id"),
        "selected_base_strategy":selected.get("base_strategy"),
        "strategy_allocation_count":len(result.get("strategy_allocations",[])),
        "final_position_multiplier":result.get("final_position_multiplier"),
        "risk_approved":result.get("risk_approved"),
        "failed_checks":result.get("failed_checks",[]),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
