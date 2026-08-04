from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v391_05a/actual/total_exposure_guard_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V391.05A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "TOTAL_EXPOSURE_GUARD_ACTIVE",
        "TOTAL_EXPOSURE_GUARD_WARNING",
        "TOTAL_EXPOSURE_GUARD_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "current_exposure_present": isinstance(evaluation.get("current_exposure"), (int, float)),
    "projected_pct_present": isinstance(evaluation.get("projected_exposure_pct"), (int, float)),
    "limit_present": isinstance(evaluation.get("maximum_total_exposure_pct"), (int, float)),
    "automatic_resize_disabled": result.get("automatic_resize_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V391.05A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
