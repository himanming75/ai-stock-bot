from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release/v392_13a/actual/paper_portfolio_reconciliation_result.json"

with path.open("r", encoding="utf-8-sig") as handle:
    result = json.load(handle)

evaluation = result.get("evaluation", {})
checks = {
    "stage": result.get("stage") == "V392.13A",
    "status": result.get("status") == "PASS",
    "state_valid": result.get("state") in {
        "PAPER_PORTFOLIO_RECONCILIATION_READY",
        "PAPER_PORTFOLIO_RECONCILIATION_BLOCKED",
    },
    "evaluation_present": isinstance(evaluation, dict),
    "portfolio_hash_present": isinstance(
        evaluation.get("portfolio_hash"), str
    ),
    "registry_hash_present": isinstance(
        evaluation.get("registry_hash"), str
    ),
    "accounting_event_hash_present": isinstance(
        evaluation.get("accounting_event_hash"), str
    ),
    "fail_closed_enabled": result.get("fail_closed_enabled") is True,
    "cash_reconciliation_enabled": (
        result.get("cash_reconciliation_enabled") is True
    ),
    "position_reconciliation_enabled": (
        result.get("position_reconciliation_enabled") is True
    ),
    "pnl_reconciliation_enabled": (
        result.get("pnl_reconciliation_enabled") is True
    ),
    "duplicate_fill_detection_enabled": (
        result.get("duplicate_fill_detection_enabled") is True
    ),
    "broker_adapter_disabled": result.get("broker_adapter_enabled") is False,
    "broker_network_disabled": result.get("broker_network_enabled") is False,
    "paper_submission_disabled": result.get("paper_submission_enabled") is False,
    "live_submission_disabled": result.get("live_submission_enabled") is False,
    "broker_write_disabled": result.get("broker_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}

verification = {
    "verification_stage": "V392.13A",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "reconciliation_valid": evaluation.get("valid") is True,
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}

print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
