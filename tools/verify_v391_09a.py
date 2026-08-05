from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v391_09a/actual/manual_resume_guard_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V391.09A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "MANUAL_RESUME_GUARD_APPROVED",
        "MANUAL_RESUME_GUARD_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "manual_resume_required": result.get("manual_resume_required") is True,
    "automatic_resume_disabled": result.get("automatic_resume_enabled") is False,
    "pause_state_after_valid": result.get("pause_state_after") in {"RUNNING", "PAUSED"},
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V391.09A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
