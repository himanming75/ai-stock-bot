
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_05_to_v82_08/actual/"
    "shadow_scheduler_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "shadow": result.get("shadow_only") is True,
    "readonly": result.get("read_only") is True,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "loop": result.get("continuous_loop_enabled") is False,
    "task": result.get("windows_task_install_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "state": result.get("state") in {
        "WAIT_AUTONOMOUS_SHADOW_CYCLE",
        "SHADOW_SCHEDULER_WAIT_INTERVAL",
        "SHADOW_SCHEDULER_CYCLE_DUE",
        "SHADOW_SCHEDULER_CYCLE_AUTHORIZED",
        "SHADOW_SCHEDULER_HEARTBEAT_TIMEOUT",
        "SHADOW_SCHEDULER_CYCLE_LATE",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
