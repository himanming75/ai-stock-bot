from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from paper_broker_adapter.engine import evaluate

def main():
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "selected_adapter":result.get("selected_adapter"),
        "adapter_name":result.get("adapter_name"),
        "read_only_adapter":result.get("read_only_adapter"),
        "safe_boundary_passed":result.get(
            "safe_api_boundary", {}
        ).get("passed"),
        "account_equity":result.get(
            "account_snapshot", {}
        ).get("equity"),
        "position_count":len(result.get("positions_snapshot",[])),
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
                / "release/v97_01_to_v97_32/actual/"
                "paper_broker_adapter_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
