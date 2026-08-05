from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_12a/actual/fill_accounting_position_update_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
portfolio = evaluation.get("portfolio_state", {})
checks = {
    "stage": result.get("stage") == "V392.12A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "FILL_ACCOUNTING_POSITION_UPDATE_READY",
        "FILL_ACCOUNTING_POSITION_UPDATE_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "portfolio_present": isinstance(portfolio, dict),
    "portfolio_hash_present": isinstance(evaluation.get("portfolio_hash"), str),
    "accounting_event_present": isinstance(
        evaluation.get("accounting_event"), dict
    ),
    "accounting_event_hash_present": isinstance(
        evaluation.get("accounting_event_hash"), str
    ),
    "partial_fill_supported": (
        result.get("partial_fill_accounting_supported") is True
    ),
    "average_cost_supported": result.get("average_cost_supported") is True,
    "realized_pnl_supported": result.get("realized_pnl_supported") is True,
    "unrealized_pnl_supported": result.get("unrealized_pnl_supported") is True,
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.12A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
