from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from long_run_qualification.config import load, validate

policy = load(ROOT)
validation = validate(policy)
checks = {
    "policy_valid": validation["valid"],
    "qualification_enabled": policy.get("qualification_enabled") is True,
    "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
    "live_submission_disabled": policy.get("live_submission_enabled") is False,
    "live_network_disabled": policy.get("live_network_enabled") is False,
    "broker_write_disabled": policy.get("broker_write_enabled") is False,
    "monitor_only": policy.get("monitor_only") is True,
    "zero_new_orders": int(policy.get("maximum_new_orders_per_day", -1)) == 0,
    "paper_endpoint_only": policy.get("paper_base_url") == "https://paper-api.alpaca.markets",
}
out = {
    "hotfix": "V321.01A",
    "stage": "V330.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k,v in checks.items() if not v],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(out, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
