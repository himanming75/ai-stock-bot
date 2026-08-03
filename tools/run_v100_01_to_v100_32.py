from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from ai_risk_manager.engine import evaluate

def main():
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "risk_assessment_id":result.get("risk_assessment_id"),
        "account_equity":result.get("account_equity"),
        "risk_score":result.get("risk_score",{}).get("risk_score"),
        "risk_level":result.get("risk_score",{}).get("risk_level"),
        "var_pct":result.get("value_at_risk",{}).get("var_pct"),
        "worst_stress_loss_pct":result.get("stress",{}).get(
            "worst_estimated_loss_pct"
        ),
        "gate_passed":result.get("pre_execution_gate",{}).get("passed"),
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
                ROOT/"release/v100_01_to_v100_32/actual/"
                "ai_risk_manager_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
