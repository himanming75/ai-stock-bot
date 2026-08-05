
from __future__ import annotations
from collections import defaultdict
from typing import Any
from .volatility_scaling import apply_volatility_scaling

def apply_sector_exposure_limits(payload: dict[str, Any]) -> dict[str, Any]:
    result = apply_volatility_scaling(payload)
    equity = float(result["account_equity"])
    limits = {str(k).upper(): float(v) for k, v in payload.get("sector_limits", {}).items()}
    default_limit = float(payload.get("default_sector_limit_pct", 0.30))
    used = defaultdict(float)
    positions = []
    for item in result["positions"]:
        sector = str(item.get("sector", "UNKNOWN")).upper()
        limit_pct = limits.get(sector, default_limit)
        capacity = max(0.0, equity * limit_pct - used[sector])
        prior = float(item["recommended_notional"])
        allowed = min(prior, capacity)
        used[sector] += allowed
        out = dict(item)
        out.update({
            "sector": sector,
            "sector_limit_pct": round(limit_pct, 6),
            "sector_capacity_before": round(capacity, 2),
            "pre_sector_notional": round(prior, 2),
            "recommended_notional": round(allowed, 2),
            "recommended_quantity": round(allowed / float(item["reference_price"]), 6),
            "binding_constraint": "SECTOR_LIMIT" if allowed + 0.01 < prior else item["binding_constraint"],
        })
        positions.append(out)
    result["positions"] = positions
    result["sector_exposure"] = {k: round(v, 2) for k, v in used.items()}
    result["total_recommended_notional"] = round(sum(p["recommended_notional"] for p in positions), 2)
    result["remaining_cash"] = round(equity - result["total_recommended_notional"], 2)
    return result
