from __future__ import annotations
from typing import Any

def adaptive_threshold(
    base_trigger_pct: float,
    volatility_pct: float,
    regime_multiplier_value: float,
    cost_bps: float,
    policy: dict[str, Any],
) -> dict[str, Any]:
    volatility_reference = float(policy.get("volatility_reference_pct", 2.0))
    volatility_sensitivity = float(policy.get("volatility_sensitivity", 0.35))
    cost_sensitivity = float(policy.get("cost_sensitivity", 0.02))
    minimum_trigger = float(policy.get("minimum_trigger_pct", 1.5))
    maximum_trigger = float(policy.get("maximum_trigger_pct", 8.0))

    volatility_ratio = volatility_pct / max(1e-9, volatility_reference)
    volatility_adjustment = 1.0 + max(0.0, volatility_ratio - 1.0) * volatility_sensitivity
    cost_adjustment = 1.0 + max(0.0, cost_bps) * cost_sensitivity / 100.0
    raw = base_trigger_pct * volatility_adjustment * regime_multiplier_value * cost_adjustment
    applied = max(minimum_trigger, min(maximum_trigger, raw))
    return {
        "base_trigger_pct": round(base_trigger_pct, 6),
        "volatility_pct": round(volatility_pct, 6),
        "regime_multiplier": round(regime_multiplier_value, 6),
        "cost_bps": round(cost_bps, 6),
        "raw_trigger_pct": round(raw, 6),
        "adaptive_trigger_pct": round(applied, 6),
    }
