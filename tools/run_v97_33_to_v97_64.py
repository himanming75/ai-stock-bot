from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from paper_broker_read_model.engine import evaluate

def main():
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "source_adapter_name":result.get("source_adapter_name"),
        "account_reconciled":result.get(
            "account_reconciliation", {}
        ).get("passed"),
        "positions_reconciled":result.get(
            "position_reconciliation", {}
        ).get("passed"),
        "snapshot_fresh":result.get(
            "snapshot_freshness", {}
        ).get("passed"),
        "integrity_passed":result.get(
            "integrity", {}
        ).get("passed"),
        "actual_credentials_used":result.get(
            "actual_credentials_used"
        ),
        "actual_external_network_used":result.get(
            "actual_external_network_used"
        ),
        "actual_orders_submitted":result.get(
            "actual_orders_submitted"
        ),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT
                / "release/v97_33_to_v97_64/actual/"
                "paper_broker_snapshot_reconciliation_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
