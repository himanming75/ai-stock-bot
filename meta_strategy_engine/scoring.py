from __future__ import annotations
from typing import Any

def normalized_score(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        return 0.0
    return max(0.0, min(1.0, (value - lower) / (upper - lower)))

def strategy_meta_score(
    strategy: dict[str, Any],
    regime_recommendations: list[str],
    stable_strategy_id: str | None,
    risk_approved: bool,
    weights: dict[str, float],
) -> dict[str, Any]:
    base = str(strategy.get("base_strategy") or strategy.get("strategy") or "")
    strategy_id = str(strategy.get("strategy_id") or "")
    full = strategy.get("full_result", strategy)
    gate = strategy.get("gate", {})
    stability = strategy.get("stability_gate", {})

    return_score = normalized_score(float(full.get("total_return_pct", 0.0)), -20.0, 50.0)
    sharpe_score = normalized_score(float(full.get("sharpe_ratio", 0.0)), -1.0, 3.0)
    drawdown_score = 1.0 - normalized_score(float(full.get("maximum_drawdown_pct", 0.0)), 0.0, 40.0)
    win_rate_score = normalized_score(float(full.get("win_rate_pct", 0.0)), 0.0, 100.0)
    regime_score = 1.0 if base in regime_recommendations else 0.25
    stable_score = 1.0 if (
        strategy_id == stable_strategy_id
        or stability.get("passed") is True
        or gate.get("approved") is True
    ) else 0.0
    risk_score = 1.0 if risk_approved else 0.0

    components = {
        "return_score": round(return_score, 4),
        "sharpe_score": round(sharpe_score, 4),
        "drawdown_score": round(drawdown_score, 4),
        "win_rate_score": round(win_rate_score, 4),
        "regime_score": round(regime_score, 4),
        "stability_score": round(stable_score, 4),
        "risk_score": round(risk_score, 4),
    }

    total = sum(
        components[name] * float(weights.get(name, 0.0))
        for name in components
    )
    return {
        "components": components,
        "meta_score": round(total, 6),
    }
