from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v331_01_to_v340_64/actual/latest_governance_result.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V340.64",
    "qualified": result.get("state") == "REAL_PAPER_OBSERVATION_GOVERNANCE_QUALIFIED",
    "status": result.get("status") == "PASS",
    "health_healthy": result.get("health") == "HEALTHY",
    "failed_empty": result.get("failed") == [],
    "incidents_empty": result.get("incidents") == [],
    "read_only_mode": result.get("governance_mode") == "READ_ONLY_MONITOR",
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "V340.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
