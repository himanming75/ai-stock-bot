import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root/"release/v141_06_to_v141_08/actual/final_validation_release_result.json"
if not path.exists():
    raise SystemExit("VERIFY=FAIL result file not found")

result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status_pass": result.get("status") == "PASS",
    "safe_false": result.get("safe_mode_engaged") is False,
    "network_zero": result.get("network_requests_executed") == 0,
    "write_zero": result.get("write_requests_executed") == 0,
    "paper_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_zero": result.get("live_orders_submitted") == 0,
    "live_disabled": result.get("live_trading_enabled") is False,
    "state_valid": result.get("state") in {
        "WAIT_OPERATIONAL_STABILITY",
        "PAPER_PRODUCTION_RELEASE_READY",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
