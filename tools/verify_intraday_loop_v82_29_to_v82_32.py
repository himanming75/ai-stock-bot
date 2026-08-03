
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_29_to_v82_32/actual/"
    "intraday_loop_result.json"
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
    "recovery": result.get("recovery_snapshot_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "INTRADAY_LOOP_WAIT_GATES",
        "INTRADAY_LOOP_READY",
        "INTRADAY_LOOP_COMPLETE",
        "INTRADAY_LOOP_RECOVERY_NOT_AVAILABLE",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
