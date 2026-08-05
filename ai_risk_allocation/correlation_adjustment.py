
from __future__ import annotations
from typing import Any
from .drawdown_scaling import apply_drawdown_scaling

def apply_correlation_adjustment(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_drawdown_scaling(payload)
    threshold = float(payload.get("correlation_threshold", 0.75))
    penalty = float(payload.get("high_correlation_multiplier", 0.70))
    corr = {}
    for item in payload.get("correlation_pairs", []):
        a, b = sorted([str(item["symbol_a"]).upper(), str(item["symbol_b"]).upper()])
        corr[(a, b)] = abs(float(item["correlation"]))
    accepted = []
    positions = []
    for item in result["positions"]:
        symbol = item["symbol"]
        max_corr = max([corr.get(tuple(sorted([symbol, other])), 0.0) for other in accepted] or [0.0])
        mult = penalty if max_corr >= threshold else 1.0
        prior = float(item["recommended_notional"])
        allowed = prior * mult
        out = dict(item)
        out.update({
            "maximum_existing_correlation": round(max_corr, 6),
            "correlation_multiplier": round(mult, 6),
            "pre_correlation_notional": round(prior, 2),
            "recommended_notional": round(allowed, 2),
            "recommended_quantity": round(allowed / float(item["reference_price"]), 6),
            "risk_at_stop": round(allowed * float(item["stop_loss_pct"]), 2),
            "binding_constraint": "CORRELATION_ADJUSTMENT" if allowed + 0.01 < prior else item["binding_constraint"],
        })
        positions.append(out)
        if allowed > 0:
            accepted.append(symbol)
    result["positions"] = positions
    result["correlation_threshold"] = round(threshold, 6)
    result["total_recommended_notional"] = round(sum(p["recommended_notional"] for p in positions), 2)
    result["total_risk_at_stop"] = round(sum(p["risk_at_stop"] for p in positions), 2)
    result["remaining_cash"] = round(float(result["account_equity"]) - result["total_recommended_notional"], 2)
    return result
