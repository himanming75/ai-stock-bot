from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v411_01_to_v420_64/actual/ai_signal_intelligence_result.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

checks = {
    "stage": result.get("stage") == "V420.64",
    "state": result.get("state") == "AI_SIGNAL_INTELLIGENCE_READY",
    "status": result.get("status") == "PASS",
    "valid_action": result.get("action") in {"BUY", "SELL", "HOLD"},
    "valid_rank": result.get("signal_rank") in {"A", "B", "C", "D"},
    "risk_score_range": 0 <= int(result.get("risk_score", -1)) <= 100,
    "network_unused": result.get("network_used") is False,
    "credentials_unused": result.get("broker_credentials_used") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "order_submission_blocked": result.get("order_submission_allowed") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "V420.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
