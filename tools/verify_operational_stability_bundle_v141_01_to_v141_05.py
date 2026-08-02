import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root/"release/v141_01_to_v141_05/actual/operational_stability_bundle_result.json"
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
    "state_valid": result.get("state") in {
        "WAIT_PAPER_INTEGRATION",
        "PAPER_RUNTIME_STABILITY_READY",
    },
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
