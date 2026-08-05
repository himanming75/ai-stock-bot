
from __future__ import annotations
import hashlib, json
from typing import Any
from .cash_reserve import apply_dynamic_cash_reserve

def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def build_integrated_allocation(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_dynamic_cash_reserve(payload)
    positions = [p for p in result["positions"] if float(p["recommended_notional"]) >= float(payload.get("minimum_notional", 1.0))]
    result["positions"] = positions
    result["total_recommended_notional"] = round(sum(float(p["recommended_notional"]) for p in positions), 2)
    result["total_risk_at_stop"] = round(sum(float(p["risk_at_stop"]) for p in positions), 2)
    result["remaining_cash"] = round(float(result["account_equity"]) - result["total_recommended_notional"], 2)
    core = {
        "positions": positions,
        "total_recommended_notional": result["total_recommended_notional"],
        "total_risk_at_stop": result["total_risk_at_stop"],
        "remaining_cash": result["remaining_cash"],
        "required_cash_reserve_amount": result["required_cash_reserve_amount"],
    }
    result["allocation_hash"] = canonical_hash(core)
    result["allocation_ready"] = bool(positions) and bool(result.get("new_risk_allowed", True))
    result["order_submission_allowed"] = False
    result["actual_paper_orders_submitted"] = 0
    result["actual_live_orders_submitted"] = 0
    return result
