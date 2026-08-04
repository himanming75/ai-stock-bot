from __future__ import annotations
from typing import Any

REGIME_BONUS = {
    "BULL_TREND": {"momentum": 12, "trend": 12, "breakout": 8, "mean_reversion": -5},
    "BEAR_TREND": {"momentum": -4, "trend": 8, "breakout": 3, "mean_reversion": 2},
    "SIDEWAYS": {"momentum": -5, "trend": -3, "breakout": -3, "mean_reversion": 12},
    "HIGH_VOLATILITY": {"momentum": -5, "trend": -2, "breakout": 5, "mean_reversion": -8},
}

def score(strategy: dict[str, Any], regime: str, policy: dict[str, Any]) -> dict[str, Any]:
    observations = int(strategy.get("observations", 0) or 0)
    win_rate = float(strategy.get("win_rate_pct", 0) or 0)
    profit_factor = float(strategy.get("profit_factor", 0) or 0)
    sharpe = float(strategy.get("sharpe", 0) or 0)
    drawdown = float(strategy.get("maximum_drawdown_pct", 0) or 0)
    confidence = float(strategy.get("signal_confidence", 0) or 0)
    strategy_type = str(strategy.get("strategy_type", strategy.get("strategy_id", "")))
    base = (
        win_rate * 0.25
        + min(profit_factor, 3.0) * 14
        + max(-1.0, min(sharpe, 3.0)) * 10
        + confidence * 0.25
        - drawdown * 1.5
    )
    adjusted = base + REGIME_BONUS.get(regime, {}).get(strategy_type, 0)
    final = max(0.0, min(100.0, adjusted))
    eligible = (
        observations >= int(policy["minimum_observations"])
        and final >= float(policy["minimum_strategy_score"])
    )
    return {
        "strategy_id": strategy.get("strategy_id"),
        "strategy_type": strategy_type,
        "symbol": strategy.get("symbol"),
        "action": str(strategy.get("action", "HOLD")).upper(),
        "score": round(final, 4),
        "signal_confidence": confidence,
        "observations": observations,
        "eligible": eligible,
    }
