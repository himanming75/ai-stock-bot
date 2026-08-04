from __future__ import annotations
from typing import Any

def estimate_cost(
    notional: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    commission_bps = float(policy.get("commission_bps", 0.0))
    slippage_bps = float(policy.get("slippage_bps", 5.0))
    spread_bps = float(policy.get("spread_bps", 2.0))
    total_bps = commission_bps + slippage_bps + spread_bps
    estimated_cost = max(0.0, notional) * total_bps / 10000.0
    return {
        "commission_bps": commission_bps,
        "slippage_bps": slippage_bps,
        "spread_bps": spread_bps,
        "total_cost_bps": round(total_bps, 6),
        "estimated_cost": round(estimated_cost, 6),
    }
