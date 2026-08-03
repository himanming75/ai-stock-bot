from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from portfolio_rebalance.engine import evaluate

def main():
    result=evaluate(ROOT)
    risk=result.get("risk",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "rebalance_id":result.get("rebalance_id"),
        "account_equity":result.get("account_equity"),
        "account_cash":result.get("account_cash"),
        "planned_intent_count":result.get("planned_intent_count",0),
        "actionable_intent_count":result.get("actionable_intent_count",0),
        "duplicate_intent_count":result.get("duplicate_intent_count",0),
        "used_turnover_pct":result.get("turnover",{}).get("used_turnover_pct"),
        "projected_cash_pct":risk.get("projected_cash_pct"),
        "risk_passed":risk.get("passed"),
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
                ROOT / "release/v99_33_to_v99_64/actual/"
                "portfolio_rebalance_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
