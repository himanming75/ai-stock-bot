from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from paper_execution_simulator.engine import simulate

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--simulation-date",default="")
    args=parser.parse_args()

    result=simulate(ROOT,args.simulation_date)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "simulation_date":result.get("simulation_date"),
        "cycle_id":result.get("cycle_id"),
        "duplicate_cycle":result.get("duplicate_cycle"),
        "simulated_orders_processed":result.get("simulated_orders_processed",0),
        "filled_count":result.get("fill_summary",{}).get("filled_count",0),
        "partial_fill_count":result.get("fill_summary",{}).get("partial_fill_count",0),
        "not_filled_count":result.get("fill_summary",{}).get("not_filled_count",0),
        "ending_cash":result.get("ending_cash"),
        "ending_equity":result.get("ending_equity"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={(ROOT/'release/v95_01_to_v95_32/actual/paper_execution_simulation_result.json').resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
