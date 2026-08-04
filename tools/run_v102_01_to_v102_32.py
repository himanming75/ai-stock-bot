from pathlib import Path
import json, sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from master_ai_orchestrator.engine import evaluate

def main() -> int:
    result = evaluate(ROOT)
    health = result.get("health", {})
    workflow = result.get("workflow", {})
    recovery = result.get("recovery_plan", {})
    checkpoint = result.get("checkpoint", {})
    summary = {
        "stage": result.get("stage"),
        "state": result.get("state"),
        "status": result.get("status"),
        "orchestration_id": result.get("orchestration_id"),
        "ready_module_count": health.get("ready_module_count"),
        "required_module_count": health.get("required_module_count"),
        "module_readiness_pct": health.get("module_readiness_pct"),
        "workflow_ready_steps": workflow.get("ready_step_count"),
        "workflow_blocked_steps": workflow.get("blocked_step_count"),
        "health_status": health.get("heartbeat_status"),
        "safety_passed": result.get("safety_lock", {}).get("passed"),
        "recovery_required": recovery.get("recovery_required"),
        "checkpoint_generation": checkpoint.get("generation"),
        "manual_approval_required": result.get("manual_approval_required"),
        "execution_authorized": result.get("execution_authorized"),
        "actual_orders_submitted": result.get("actual_orders_submitted"),
        "paper_only": result.get("paper_only"),
        "next_phase": result.get("next_phase"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(
        "RESULT_FILE="
        + str(
            (
                ROOT / "release/v102_01_to_v102_32/actual/"
                "master_ai_orchestrator_result.json"
            ).resolve()
        )
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
