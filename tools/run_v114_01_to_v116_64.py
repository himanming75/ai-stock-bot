from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_safe_execution.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "execution_package_id":result.get("execution_package_id"),
        "selected_adapter":result.get("selected_adapter"),
        "account_equity":result.get("account_equity"),
        "intent_count":len(result.get("order_intents",[])),
        "valid_intent_count":result.get(
            "validation",{}
        ).get("valid_count"),
        "invalid_intent_count":result.get(
            "validation",{}
        ).get("invalid_count"),
        "queue_count":result.get(
            "execution_queue",{}
        ).get("queue_count"),
        "ready_for_approval_count":result.get(
            "execution_queue",{}
        ).get("ready_for_approval_count"),
        "manual_approval_required":result.get(
            "manual_approval_required"
        ),
        "approval_granted":result.get("approval_granted"),
        "approval_token_issued":result.get("approval_token_issued"),
        "real_broker_submission_attempted":result.get(
            "real_broker_submission_attempted"
        ),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v114_01_to_v116_64/actual/"
                "broker_safe_execution_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
