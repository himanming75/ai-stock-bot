from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v391_10a/actual/risk_governor_integration_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V391.10A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "RISK_GOVERNOR_INTEGRATION_READY",
        "RISK_GOVERNOR_INTEGRATION_WARNING",
        "RISK_GOVERNOR_INTEGRATION_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "decision_valid": result.get("risk_governor_decision") in {
        "ALLOW", "WARN", "BLOCKED"
    },
    "policy_hash_consistent": evaluation.get("policy_hash_consistent") is True,
    "execution_authorization_disabled": (
        result.get("execution_authorization_allowed") is False
    ),
    "automatic_resume_disabled": result.get("automatic_resume_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V391.10A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
