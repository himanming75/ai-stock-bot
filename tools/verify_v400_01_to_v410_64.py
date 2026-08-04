from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "release/v400_01_to_v410_64/actual/offline_ai_decision_result.json"

with RESULT.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V410.64",
    "state": result.get("state") == "OFFLINE_AI_DECISION_ENGINE_READY",
    "status": result.get("status") == "PASS",
    "network_unused": result.get("network_used") is False,
    "credentials_unused": result.get("broker_credentials_used") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "valid_action": result.get("action") in {"BUY", "SELL", "HOLD"},
}
verification = {
    "verification_stage": "V410.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
