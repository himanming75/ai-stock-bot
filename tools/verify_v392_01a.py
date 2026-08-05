from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_01a/actual/execution_authorization_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V392.01A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "EXECUTION_AUTHORIZATION_APPROVED",
        "EXECUTION_AUTHORIZATION_BLOCKED",
    },
    "policy_valid": result.get("policy_validation", {}).get("valid") is True,
    "manual_approval_required": result.get("manual_approval_required") is True,
    "automatic_authorization_disabled": (
        result.get("automatic_authorization_enabled") is False
    ),
    "paper_only": result.get("paper_endpoint_only") is True,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.01A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
