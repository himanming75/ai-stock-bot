from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from risk_budget.engine import evaluate

def main():
    result=evaluate(ROOT)
    allocation=result.get("risk_budget_allocation",{})
    exposure=result.get("dynamic_exposure_control",{})
    heat=result.get("portfolio_heat",{})
    gate=result.get("risk_budget_gate",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "risk_budget_id":result.get("risk_budget_id"),
        "candidate_count":result.get("candidate_count",0),
        "used_risk_budget_pct":allocation.get("used_risk_budget_pct"),
        "unused_risk_budget_pct":allocation.get("unused_risk_budget_pct"),
        "final_exposure_multiplier":exposure.get("final_exposure_multiplier"),
        "target_gross_exposure_pct":exposure.get("target_gross_exposure_pct"),
        "portfolio_heat_pct":heat.get("portfolio_heat_pct"),
        "gate_passed":gate.get("passed"),
        "manual_approval_required":result.get("manual_approval_required"),
        "execution_authorized":result.get("execution_authorized"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT/"release/v100_33_to_v100_64/actual/"
                "risk_budget_allocation_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
