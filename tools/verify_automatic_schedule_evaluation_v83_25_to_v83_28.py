
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v83_25_to_v83_28/actual/"
    "automatic_schedule_evaluation_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "paper": result.get("paper_only") is True,
    "supervised": result.get("operator_supervision_required") is True,
    "trigger_execution": (
        result.get("local_trigger_execution_enabled") is False
    ),
    "task": result.get("windows_task_install_enabled") is False,
    "loop": result.get("continuous_loop_enabled") is False,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "orders_sent": result.get("actual_paper_orders_submitted") == 0,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "LOCAL_TRIGGER_READY",
        "AUTOMATIC_SCHEDULE_WAIT_GATES",
        "LOCAL_TRIGGER_IN_PROGRESS",
        "LOCAL_TRIGGER_CREATED",
        "LOCAL_TRIGGER_COMPLETED",
        "NO_ACTIVE_LOCAL_TRIGGER",
        "LOCAL_TRIGGER_LOCK_CLEARED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
