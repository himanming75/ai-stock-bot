from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from live_broker_readonly.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "snapshot_id":result.get("snapshot_id"),
        "selected_adapter":result.get("selected_adapter"),
        "supported_adapter_count":len(
            result.get("supported_adapters",[])
        ),
        "adapter_healthy":result.get(
            "adapter_health",{}
        ).get("healthy"),
        "account_equity":result.get(
            "account_snapshot",{}
        ).get("equity"),
        "position_count":len(result.get("position_snapshot",[])),
        "order_count":len(result.get("order_snapshot",[])),
        "account_reconciled":result.get(
            "reconciliation",{}
        ).get("account_reconciled"),
        "positions_reconciled":result.get(
            "reconciliation",{}
        ).get("positions_reconciled"),
        "drift_detected":result.get("drift",{}).get("drift_detected"),
        "fixture_snapshot_used":result.get("fixture_snapshot_used"),
        "real_network_connection_attempted":result.get(
            "real_network_connection_attempted"
        ),
        "actual_credentials_used":result.get("actual_credentials_used"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "read_only":result.get("read_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v111_01_to_v113_64/actual/"
                "live_broker_readonly_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
