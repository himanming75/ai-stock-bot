import json
from pathlib import Path
path = Path(__file__).resolve().parents[1]/"release/op1_05_to_op1_08/actual/daily_read_only_observation_result.json"
if not path.exists():
    raise SystemExit("VERIFY=FAIL result missing")
r = json.loads(path.read_text(encoding="utf-8"))
checks = {
    "status": r.get("status") == "PASS",
    "safe": r.get("safe_mode_engaged") is False,
    "network": r.get("network_requests_executed") == 0,
    "write": r.get("write_requests_executed") == 0,
    "paper": r.get("actual_paper_orders_submitted") == 0,
    "live": r.get("live_orders_submitted") == 0,
    "submission_disabled": r.get("order_submission_enabled") is False,
    "live_disabled": r.get("live_trading_enabled") is False,
    "state": r.get("state") in {
        "WAIT_PAPER_OPERATIONS_PILOT",
        "DAILY_READ_ONLY_OBSERVATION_READY",
    },
}
failed = [k for k,v in checks.items() if not v]
if failed:
    raise SystemExit("VERIFY=FAIL " + ",".join(failed))
print("VERIFY=PASS")
