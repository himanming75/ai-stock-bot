from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v391_01a/actual/risk_policy_validation_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V391.01A",
    "state_ready": result.get("state") == "RISK_POLICY_READY",
    "status": result.get("status") == "PASS",
    "policy_valid": result.get("validation", {}).get("valid") is True,
    "errors_empty": result.get("validation", {}).get("errors") == [],
    "hash_present": isinstance(result.get("policy_hash"), str) and len(result.get("policy_hash")) == 64,
    "risk_operations_allowed": result.get("risk_operations_allowed") is True,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V391.01A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
