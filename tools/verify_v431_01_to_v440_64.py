from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v431_01_to_v440_64/actual/ai_strategy_selection_result.json"
with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

allowed = {"TREND_FOLLOWING", "MOMENTUM", "BREAKOUT", "MEAN_REVERSION", "CASH_DEFENSIVE"}
checks = {
    "stage": result.get("stage") == "V440.64",
    "state": result.get("state") == "AI_STRATEGY_SELECTION_READY",
    "status": result.get("status") == "PASS",
    "selected_strategy_valid": result.get("selected_strategy") in allowed,
    "fallback_strategy_valid": result.get("fallback_strategy") in allowed,
    "network_unused": result.get("network_used") is False,
    "credentials_unused": result.get("broker_credentials_used") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "order_submission_blocked": result.get("order_submission_allowed") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "V440.64",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
