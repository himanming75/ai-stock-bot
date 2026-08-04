from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from final_system_integration.engine import evaluate

def main() -> int:
    result=evaluate(ROOT)
    readiness=result.get("readiness",{})
    pipeline=result.get("pipeline",{})
    summary={
        "stage":result.get("stage"),
        "state":result.get("state"),
        "status":result.get("status"),
        "integration_id":result.get("integration_id"),
        "readiness_score":readiness.get("readiness_score"),
        "readiness_level":readiness.get("readiness_level"),
        "ready_module_count":readiness.get("ready_module_count"),
        "module_count":readiness.get("module_count"),
        "pipeline_ready_steps":pipeline.get("ready_steps"),
        "pipeline_total_steps":pipeline.get("total_steps"),
        "safety_passed":result.get("safety",{}).get("passed"),
        "final_release_eligible":result.get("final_release_eligible"),
        "production_release_created":result.get("production_release_created"),
        "manual_approval_required":result.get("manual_approval_required"),
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
                ROOT/"release/v105_01_to_v105_32/actual/"
                "final_system_integration_result.json"
            ).resolve()
        )
    )
    return 0

if __name__=="__main__":
    raise SystemExit(main())
