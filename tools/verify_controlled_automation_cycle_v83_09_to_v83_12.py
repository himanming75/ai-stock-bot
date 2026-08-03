
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v83_09_to_v83_12/actual/"
    "controlled_automation_cycle_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "paper": result.get("paper_only") is True,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "broker_commands": (
        result.get("broker_command_execution_enabled") is False
    ),
    "loop": result.get("continuous_loop_enabled") is False,
    "max_actions": result.get("max_actions_per_cycle") == 1,
    "network": result.get("network_requests_executed") == 0,
    "orders_sent": result.get("actual_paper_orders_submitted") == 0,
    "recovery": result.get("recovery_snapshot_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "CONTROLLED_CYCLE_WAIT_GATES",
        "CONTROLLED_CYCLE_READY",
        "CONTROLLED_AUTOMATION_CYCLE_COMPLETE",
        "CONTROLLED_CYCLE_RECOVERY_NOT_AVAILABLE",
        "CONTROLLED_CYCLE_LOCK_CLEARED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
