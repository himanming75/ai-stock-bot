from __future__ import annotations

SCENARIOS = {
    "NORMAL": {
        "return_multiplier": 1.0,
        "risk_multiplier": 1.0,
        "correlation_add": 0.0,
    },
    "CORRECTION": {
        "return_multiplier": -0.55,
        "risk_multiplier": 1.8,
        "correlation_add": 0.12,
    },
    "SELL_OFF": {
        "return_multiplier": -1.35,
        "risk_multiplier": 2.8,
        "correlation_add": 0.25,
    },
    "VOLATILITY_SPIKE": {
        "return_multiplier": 0.20,
        "risk_multiplier": 3.2,
        "correlation_add": 0.18,
    },
    "CORRELATION_SHOCK": {
        "return_multiplier": -0.35,
        "risk_multiplier": 2.1,
        "correlation_add": 0.40,
    },
}


def run_stress_scenarios(
    analyses: list[dict],
    weights: dict[str, float],
    average_abs_correlation: float,
) -> list[dict]:
    results = []
    for name, config in SCENARIOS.items():
        portfolio_return = 0.0
        portfolio_risk = 0.0
        for item in analyses:
            symbol = item["symbol"]
            weight = weights.get(symbol, 0.0)
            portfolio_return += (
                float(item.get("expected_return", 0.0))
                * config["return_multiplier"]
                * weight
            )
            portfolio_risk += (
                float(item.get("expected_risk", 0.0))
                * config["risk_multiplier"]
                * weight
            )

        shocked_correlation = min(
            1.0,
            average_abs_correlation + config["correlation_add"],
        )
        correlation_penalty = shocked_correlation * portfolio_risk * 0.35
        stressed_return = portfolio_return - correlation_penalty
        stressed_drawdown = max(
            0.0,
            portfolio_risk + max(0.0, -stressed_return),
        )

        results.append({
            "scenario": name,
            "portfolio_return": round(stressed_return, 6),
            "portfolio_risk": round(portfolio_risk, 6),
            "shocked_correlation": round(shocked_correlation, 6),
            "estimated_drawdown": round(stressed_drawdown, 6),
            "simulation_only": True,
        })
    return results
