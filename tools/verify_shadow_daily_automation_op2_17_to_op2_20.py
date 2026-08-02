import json
from pathlib import Path

path = (
    Path(__file__).resolve().parents[1]
    / "release/op2_17_to_op2_20/actual/shadow_daily_automation_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "safe": result.get("safe_mode_engaged") is False,
    "network": result.get("network_requests_executed") == 0,
    "write": result.get("write_requests_executed") == 0,
    "paper": result.get("actual_paper_orders_submitted") == 0,
    "live": result.get("live_orders_submitted") == 0,
    "shadow": result.get("shadow_only") is True,
    "submission": result.get("order_submission_enabled") is False,
    "continuous_loop": result.get("continuous_loop_enabled") is False,
    "task_not_installed": result.get("automatic_task_installed") is False,
    "state": result.get("state") in {
        "WAIT_AUTOMATIC_SHADOW_PIPELINE",
        "SHADOW_DAILY_AUTOMATION_READY",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
