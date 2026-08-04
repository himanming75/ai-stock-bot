from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v421_01_to_v430_64/actual/ai_portfolio_intelligence_result.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

selected = result.get("selected", [])
cash = float(result.get("cash_weight", -1))
total = float(result.get("total_selected_weight", -1))
checks = {
    "stage": result.get("stage") == "V430.64",
    "state": result.get("state") == "AI_PORTFOLIO_INTELLIGENCE_READY",
    "status": result.get("status") == "PASS",
    "weights_sum": abs((cash + total) - 1.0) <= 0.001,
    "weights_nonnegative": all(float(item.get("weight", -1)) >= 0 for item in selected),
    "network_unused": result.get("network_used") is False,
    "credentials_unused": result.get("broker_credentials_used") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "order_submission_blocked": result.get("order_submission_allowed") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "V430.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
