from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from decision_orchestrator.engine import evaluate

def main():
    result=evaluate(ROOT)
    plans=result.get("paper_order_plans",[])
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "source_paper_decision":result.get("source_paper_decision"),
        "planned_order_count":sum(1 for row in plans if row.get("state")=="PLANNED"),
        "duplicate_block_count":sum(1 for row in plans if row.get("state")=="BLOCKED_DUPLICATE"),
        "skipped_plan_count":sum(1 for row in plans if row.get("state")=="SKIPPED"),
        "total_planned_notional":result.get("gates",{}).get("total_planned_notional"),
        "manual_approval_required":result.get("manual_approval_required"),
        "execution_authorized":result.get("execution_authorized"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(f"RESULT_FILE={(ROOT/'release/v94_33_to_v94_64/actual/paper_execution_plan.json').resolve()}")
    return 0

if __name__=="__main__": raise SystemExit(main())
