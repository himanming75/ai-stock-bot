from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v371_01_to_v380_64/actual/latest_lifecycle_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V380.64",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "PAPER_EXECUTION_LIFECYCLE_READY_BLOCKED",
        "PAPER_EXECUTION_LIFECYCLE_ACTIVE",
    },
    "read_only": result.get("read_only") is True,
    "paper_endpoint_only": result.get("paper_endpoint_only") is True,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "summary_present": isinstance(result.get("summary"), dict),
    "reconciliation_present": isinstance(result.get("position_reconciliation"), dict),
}

verification = {
    "verification_stage": "V380.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
