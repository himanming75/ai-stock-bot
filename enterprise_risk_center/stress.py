from __future__ import annotations
from typing import Any

DEFAULT_SCENARIOS = [
    {"name": "MILD_CORRECTION", "return_shock_pct": -5.0, "volatility_multiplier": 1.25},
    {"name": "BEAR_MARKET", "return_shock_pct": -20.0, "volatility_multiplier": 1.75},
    {"name": "FLASH_CRASH", "return_shock_pct": -12.0, "volatility_multiplier": 2.50},
    {"name": "VOLATILITY_SPIKE", "return_shock_pct": -3.0, "volatility_multiplier": 3.00},
]

def run_stress_scenarios(
    portfolio_value: float,
    volatility_pct: float,
    allocations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    concentration = max(
        (float(item.get("weight_pct", 0.0)) for item in allocations),
        default=0.0,
    ) / 100.0
    output = []
    for scenario in DEFAULT_SCENARIOS:
        shock = float(scenario["return_shock_pct"])
        vol_multiplier = float(scenario["volatility_multiplier"])
        concentration_penalty = concentration * abs(shock) * 0.20
        estimated_loss_pct = abs(shock) + concentration_penalty
        stressed_value = portfolio_value * (1.0 - estimated_loss_pct / 100.0)
        output.append({
            **scenario,
            "concentration_penalty_pct": round(concentration_penalty, 4),
            "estimated_loss_pct": round(estimated_loss_pct, 4),
            "estimated_loss_amount": round(
                portfolio_value - stressed_value, 4
            ),
            "stressed_portfolio_value": round(stressed_value, 4),
            "stressed_volatility_pct": round(
                volatility_pct * vol_multiplier, 4
            ),
        })
    return output
