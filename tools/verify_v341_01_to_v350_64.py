from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v341_01_to_v350_64/actual/latest_governed_decision.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

candidate = result.get("paper_order_candidate", {})
checks = {
    "stage": result.get("stage") == "V350.64",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {"GOVERNED_DECISION_CANDIDATE_READY", "GOVERNED_DECISION_BLOCKED"},
    "candidate_present": bool(candidate),
    "submission_blocked": candidate.get("submission_allowed") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "hash_present": isinstance(result.get("decision_hash"), str) and len(result.get("decision_hash")) == 64,
    "replayable": result.get("replayable") is True,
}
verification = {
    "verification_stage": "V350.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
