from __future__ import annotations
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "release/v139_09/actual/active_order_lifecycle_monitor_result.json"
if not path.exists():
    raise SystemExit("VERIFY=FAIL result file not found")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status_pass": result.get("status") == "PASS",
    "safe_mode_false": result.get("safe_mode_engaged") is False,
    "credentials_false": result.get("actual_credentials_used") is False,
    "network_false": result.get("actual_external_network_used") is False,
    "network_zero": result.get("network_requests_executed") == 0,
    "write_zero": result.get("write_requests_executed") == 0,
    "paper_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_zero": result.get("live_orders_submitted") == 0,
    "next_order_false": result.get("next_order_allowed") is False,
    "state_valid": result.get("state") in {
        "WAIT_ACCEPTANCE",
        "ACTIVE_ORDER_MONITORING",
        "PARTIALLY_FILLED",
        "TERMINAL_OBSERVED",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
