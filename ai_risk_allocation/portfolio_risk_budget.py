
from __future__ import annotations
from typing import Any
from .sector_exposure import apply_sector_exposure_limits

def apply_portfolio_risk_budget(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_sector_exposure_limits(payload)
    equity = float(result["account_equity"])
    max_risk = equity * float(payload.get("maximum_portfolio_risk_pct", 0.03))
    used = 0.0
    positions = []
    for item in result["positions"]:
        stop = float(item["stop_loss_pct"])
        prior = float(item["recommended_notional"])
        capacity_notional = max(0.0, (max_risk - used) / stop) if stop > 0 else 0.0
        allowed = min(prior, capacity_notional)
        risk = allowed * stop
        used += risk
        out = dict(item)
        out.update({
            "pre_risk_budget_notional": round(prior, 2),
            "recommended_notional": round(allowed, 2),
            "recommended_quantity": round(allowed / float(item["reference_price"]), 6),
            "risk_at_stop": round(risk, 2),
            "portfolio_risk_used_after": round(used, 2),
            "binding_constraint": "PORTFOLIO_RISK_BUDGET" if allowed + 0.01 < prior else item["binding_constraint"],
        })
        positions.append(out)
    result["positions"] = positions
    result["maximum_portfolio_risk_amount"] = round(max_risk, 2)
    result["total_risk_at_stop"] = round(used, 2)
    result["remaining_risk_budget"] = round(max(0.0, max_risk - used), 2)
    result["total_recommended_notional"] = round(sum(p["recommended_notional"] for p in positions), 2)
    result["remaining_cash"] = round(equity - result["total_recommended_notional"], 2)
    return result
