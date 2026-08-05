
from __future__ import annotations
from typing import Any
from .portfolio_risk_budget import apply_portfolio_risk_budget

def drawdown_multiplier(drawdown_pct: float, tiers: list[dict[str, Any]]) -> float:
    if drawdown_pct < 0:
        raise ValueError("DRAWDOWN_PCT_MUST_BE_NONNEGATIVE")
    for tier in sorted(tiers, key=lambda x: float(x["max_drawdown_pct"])):
        if drawdown_pct <= float(tier["max_drawdown_pct"]):
            return float(tier["multiplier"])
    return 0.0

def apply_drawdown_scaling(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_portfolio_risk_budget(payload)
    dd = float(payload.get("current_drawdown_pct", 0.0))
    tiers = payload.get("drawdown_tiers", [
        {"max_drawdown_pct": 0.03, "multiplier": 1.0},
        {"max_drawdown_pct": 0.06, "multiplier": 0.75},
        {"max_drawdown_pct": 0.10, "multiplier": 0.50},
    ])
    mult = drawdown_multiplier(dd, tiers)
    positions = []
    for item in result["positions"]:
        prior = float(item["recommended_notional"])
        allowed = prior * mult
        out = dict(item)
        out.update({
            "current_drawdown_pct": round(dd, 6),
            "drawdown_multiplier": round(mult, 6),
            "pre_drawdown_notional": round(prior, 2),
            "recommended_notional": round(allowed, 2),
            "recommended_quantity": round(allowed / float(item["reference_price"]), 6),
            "risk_at_stop": round(allowed * float(item["stop_loss_pct"]), 2),
            "binding_constraint": "DRAWDOWN_SCALING" if allowed + 0.01 < prior else item["binding_constraint"],
        })
        positions.append(out)
    result["positions"] = positions
    result["drawdown_multiplier"] = round(mult, 6)
    result["new_risk_allowed"] = mult > 0
    result["total_recommended_notional"] = round(sum(p["recommended_notional"] for p in positions), 2)
    result["total_risk_at_stop"] = round(sum(p["risk_at_stop"] for p in positions), 2)
    result["remaining_cash"] = round(float(result["account_equity"]) - result["total_recommended_notional"], 2)
    return result
