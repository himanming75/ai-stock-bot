
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v83_05_to_v83_08/actual/"
    "local_action_dispatcher_result.json"
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
    "auto_execution": (
        result.get("automatic_action_execution_enabled") is False
    ),
    "loop": result.get("continuous_loop_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "orders_sent": result.get("actual_paper_orders_submitted") == 0,
    "recovery": result.get("recovery_snapshot_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "WAIT_AUTHORIZED_ORCHESTRATOR_ACTION",
        "LOCAL_ACTION_READY",
        "LOCAL_ACTION_DRY_RUN_COMPLETE",
        "LOCAL_ACTION_DISPATCH_COMPLETE",
        "LOCAL_DISPATCH_LOCK_CLEARED",
        "ORCHESTRATOR_NO_ACTIVE_ACTION",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
