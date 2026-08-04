from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from continuous_autonomous_engine.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    selected=result.get("selected_session",{}).get("session") or {}
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "engine_id":result.get("engine_id"),
        "engine_action":result.get("engine_action"),
        "selected_session_id":selected.get("session_id"),
        "selected_session_date":selected.get("session_date"),
        "completed_phase_count":result.get("completed_phase_count"),
        "failed_phases":result.get("failed_phases"),
        "gates_passed":result.get("iteration_gates",{}).get("passed"),
        "recovery_required":result.get("recovery",{}).get("recovery_required"),
        "checkpoint_generation":result.get("checkpoint",{}).get("generation"),
        "continuous_service_started":result.get("continuous_service_started"),
        "manual_approval_required":result.get("manual_approval_required"),
        "approval_granted":result.get("approval_granted"),
        "execution_authorized":result.get("execution_authorized"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v104_01_to_v104_32/actual/"
                "continuous_autonomous_engine_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
