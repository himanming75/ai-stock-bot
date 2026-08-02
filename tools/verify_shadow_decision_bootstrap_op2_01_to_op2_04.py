import json
from pathlib import Path

path = (
    Path(__file__).resolve().parents[1]
    / "release/op2_01_to_op2_04/actual/shadow_decision_bootstrap_result.json"
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
    "shadow_only": result.get("shadow_only") is True,
    "submission_disabled": (
        result.get("order_submission_enabled") is False
    ),
    "broker_write_disabled": (
        result.get("broker_write_enabled") is False
    ),
    "state": result.get("state") in {
        "WAIT_WINDOWS_SCHEDULED_COLLECTION",
        "SHADOW_DECISION_READY",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
