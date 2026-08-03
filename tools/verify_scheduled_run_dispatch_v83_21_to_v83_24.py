
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v83_21_to_v83_24/actual/"
    "scheduled_run_dispatch_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "paper": result.get("paper_only") is True,
    "supervised": result.get("operator_supervision_required") is True,
    "single": result.get("max_dispatches_per_authorization") == 1,
    "task": result.get("windows_task_install_enabled") is False,
    "loop": result.get("continuous_loop_enabled") is False,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "orders_sent": result.get("actual_paper_orders_submitted") == 0,
    "recovery": result.get("recovery_snapshot_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "WAIT_SCHEDULED_RUN_AUTHORIZATION",
        "SCHEDULED_DISPATCH_READY",
        "SCHEDULED_DISPATCH_DRY_RUN_COMPLETE",
        "SCHEDULED_DISPATCH_COMPLETE",
        "SCHEDULED_DISPATCH_LOCK_CLEARED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
