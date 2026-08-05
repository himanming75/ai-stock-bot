
from __future__ import annotations
from typing import Any
from .integrated_allocation import build_integrated_allocation

def qualify_allocation(payload: dict[str, Any]) -> dict[str, Any]:
    result = build_integrated_allocation(payload)
    equity = float(result["account_equity"])
    checks = {
        "allocation_ready": result["allocation_ready"] is True,
        "allocation_hash_present": len(result["allocation_hash"]) == 64,
        "notional_within_equity": result["total_recommended_notional"] <= equity + 0.01,
        "cash_reserve_satisfied": result["remaining_cash"] + 0.01 >= result["required_cash_reserve_amount"],
        "risk_budget_satisfied": result["total_risk_at_stop"] <= result["maximum_portfolio_risk_amount"] + 0.01,
        "all_positions_nonnegative": all(float(p["recommended_notional"]) >= 0 for p in result["positions"]),
        "paper_orders_zero": result["actual_paper_orders_submitted"] == 0,
        "live_orders_zero": result["actual_live_orders_submitted"] == 0,
        "submission_disabled": result["order_submission_allowed"] is False,
    }
    result["qualification_checks"] = checks
    result["qualification_status"] = "PASS" if all(checks.values()) else "FAIL"
    result["qualified"] = all(checks.values())
    result["failed_checks"] = [k for k, v in checks.items() if not v]
    return result
