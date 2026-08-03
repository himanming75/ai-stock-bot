
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_25_to_v82_28/actual/"
    "paper_scheduler_result.json"
)
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": result.get("status") == "PASS",
    "paper": result.get("paper_only") is True,
    "readonly": result.get("read_only") is True,
    "broker": result.get("broker_write_enabled") is False,
    "orders": result.get("order_submission_enabled") is False,
    "loop": result.get("continuous_loop_enabled") is False,
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "WAIT_PAPER_SESSION_RUNNING",
        "PAPER_SCHEDULER_HEARTBEAT_TIMEOUT",
        "PAPER_SCHEDULER_WAIT_INTERVAL",
        "PAPER_SCHEDULER_TICK_DUE",
        "PAPER_SCHEDULER_TICK_LATE",
        "PAPER_SCHEDULER_TICK_AUTHORIZED",
        "PAPER_SCHEDULER_TICK_COMPLETED",
        "PAPER_SCHEDULER_NO_ACTIVE_TICK",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
