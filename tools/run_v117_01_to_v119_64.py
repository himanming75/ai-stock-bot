from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from live_safety_system.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "safety_assessment_id":result.get("safety_assessment_id"),
        "safety_passed":result.get("safety_passed"),
        "kill_switch_triggered":result.get(
            "kill_switch",{}
        ).get("triggered"),
        "daily_loss_within_limit":result.get(
            "loss_limits",{}
        ).get("checks",{}).get("daily_loss_within_limit"),
        "weekly_loss_within_limit":result.get(
            "loss_limits",{}
        ).get("checks",{}).get("weekly_loss_within_limit"),
        "exposure_passed":result.get("exposure",{}).get("passed"),
        "anomaly_detected":result.get(
            "anomaly_detection",{}
        ).get("detected"),
        "emergency_shutdown_required":result.get(
            "emergency_action",{}
        ).get("emergency_shutdown_required"),
        "resume_allowed":result.get(
            "resume_gate",{}
        ).get("resume_allowed"),
        "manual_approval_required":result.get(
            "manual_approval_required"
        ),
        "approval_granted":result.get("approval_granted"),
        "actual_orders_submitted":result.get("actual_orders_submitted"),
        "paper_only":result.get("paper_only"),
        "next_phase":result.get("next_phase"),
    }
    print(json.dumps(summary,indent=2,sort_keys=True))
    print(
        "RESULT_FILE="
        +str(
            (
                ROOT/"release/v117_01_to_v119_64/actual/"
                "live_safety_system_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
