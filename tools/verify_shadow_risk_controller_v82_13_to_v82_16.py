
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = (
    ROOT / "release/v82_13_to_v82_16/actual/"
    "shadow_risk_controller_result.json"
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
    "network": result.get("network_requests_executed") == 0,
    "writes": result.get("write_requests_executed") == 0,
    "kill": result.get("kill_switch_written") is True,
    "recovery": result.get("recovery_lock_written") is True,
    "report": result.get("risk_report_written") is True,
    "dashboard": result.get("dashboard_state_written") is True,
    "state": result.get("state") in {
        "SHADOW_RISK_CLEAR",
        "SHADOW_RISK_KILL_SWITCH_ACTIVE",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
