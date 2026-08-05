
from __future__ import annotations
from typing import Any
from .correlation_adjustment import apply_correlation_adjustment

def apply_dynamic_cash_reserve(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_correlation_adjustment(payload)
    equity = float(result["account_equity"])
    base = float(payload.get("minimum_cash_reserve_pct", 0.10))
    volatility_add = float(payload.get("high_volatility_cash_add_pct", 0.10)) if float(payload.get("market_volatility", 0.0)) >= float(payload.get("high_volatility_threshold", 0.30)) else 0.0
    drawdown_add = float(payload.get("drawdown_cash_add_pct", 0.10)) if float(payload.get("current_drawdown_pct", 0.0)) >= float(payload.get("cash_drawdown_threshold", 0.05)) else 0.0
    reserve_pct = min(float(payload.get("maximum_cash_reserve_pct", 0.50)), base + volatility_add + drawdown_add)
    investable = equity * (1.0 - reserve_pct)
    prior_total = sum(float(p["recommended_notional"]) for p in result["positions"])
    scale = min(1.0, investable / prior_total) if prior_total > 0 else 1.0
    positions = []
    for item in result["positions"]:
        prior = float(item["recommended_notional"])
        allowed = prior * scale
        out = dict(item)
        out.update({
            "cash_reserve_pct": round(reserve_pct, 6),
            "cash_reserve_multiplier": round(scale, 6),
            "pre_cash_reserve_notional": round(prior, 2),
            "recommended_notional": round(allowed, 2),
            "recommended_quantity": round(allowed / float(item["reference_price"]), 6),
            "risk_at_stop": round(allowed * float(item["stop_loss_pct"]), 2),
            "binding_constraint": "CASH_RESERVE" if allowed + 0.01 < prior else item["binding_constraint"],
        })
        positions.append(out)
    result["positions"] = positions
    result["required_cash_reserve_pct"] = round(reserve_pct, 6)
    result["required_cash_reserve_amount"] = round(equity * reserve_pct, 2)
    result["maximum_investable_amount"] = round(investable, 2)
    result["total_recommended_notional"] = round(sum(p["recommended_notional"] for p in positions), 2)
    result["total_risk_at_stop"] = round(sum(p["risk_at_stop"] for p in positions), 2)
    result["remaining_cash"] = round(equity - result["total_recommended_notional"], 2)
    return result
