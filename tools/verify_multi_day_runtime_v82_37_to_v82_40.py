
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_37_to_v82_40/actual/"
    "multi_day_runtime_result.json"
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
    "auto_start": (
        result.get("automatic_session_start_enabled") is False
    ),
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "WAIT_DAILY_CERTIFICATION",
        "WAIT_NEXT_DAY_PREPARATION",
        "MULTI_DAY_RUNTIME_WAIT_GATES",
        "MULTI_DAY_ROLLOVER_READY",
        "MULTI_DAY_ROLLOVER_COMPLETE",
        "MULTI_DAY_RUNTIME_RESET",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
