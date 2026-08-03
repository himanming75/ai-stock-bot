
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_21_to_v82_24/actual/"
    "paper_session_manager_result.json"
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
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "WAIT_TRADE_AUTHORIZATION",
        "PAPER_SESSION_MARKET_HOLIDAY_OR_WEEKEND",
        "PAPER_SESSION_WAIT_MARKET_OPEN",
        "PAPER_SESSION_READY_TO_START",
        "PAPER_SESSION_RUNNING",
        "PAPER_SESSION_CLOSED",
        "PAPER_SESSION_NOT_ACTIVE",
        "PAPER_SESSION_RECOVERY_NOT_AVAILABLE",
        "PAPER_SESSION_RECOVERED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
