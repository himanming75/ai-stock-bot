import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
path = root/"release/v140_10_to_v140_12/actual/alpaca_paper_integration_bundle_result.json"
if not path.exists():
    raise SystemExit("VERIFY=FAIL result file not found")
result = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status_pass": result.get("status") == "PASS",
    "safe_false": result.get("safe_mode_engaged") is False,
    "live_zero": result.get("live_orders_submitted") == 0,
    "state_valid": result.get("state") in {
        "WAIT_AUTONOMOUS_ENGINE",
        "PAPER_INTEGRATION_READY_SUBMISSION_DISABLED",
        "ACTUAL_PAPER_AUTONOMOUS_READY",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
