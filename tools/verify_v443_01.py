from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v443_01/actual/volatility_scaling_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

positions = result.get("positions", [])
checks = {
    "stage": result.get("stage") == "V443.01",
    "state": result.get("state") == "VOLATILITY_SCALING_READY",
    "status": result.get("status") == "PASS",
    "positions_present": len(positions) > 0,
    "multiplier_bounds": all(
        float(result["minimum_volatility_multiplier"])
        <= float(item["volatility_multiplier"])
        <= float(result["maximum_volatility_multiplier"])
        for item in positions
    ),
    "notional_not_increased": all(
        float(item["recommended_notional"]) <= float(item["pre_volatility_notional"]) + 0.01
        for item in positions
    ),
    "network_unused": result.get("network_used") is False,
    "credentials_unused": result.get("broker_credentials_used") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "order_submission_blocked": result.get("order_submission_allowed") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V443.01",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
