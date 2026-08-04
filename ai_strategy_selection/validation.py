from __future__ import annotations
from typing import Any


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    regime = str(payload.get("market_regime", "")).strip().upper()
    if regime not in {"BULL_TREND", "BEAR_TREND", "RANGE", "HIGH_VOLATILITY"}:
        errors.append("MARKET_REGIME_INVALID")

    for name in (
        "trend_strength",
        "momentum_strength",
        "breakout_strength",
        "mean_reversion_strength",
        "volatility_score",
        "liquidity_score",
        "breadth_score",
    ):
        try:
            value = float(payload.get(name))
        except (TypeError, ValueError):
            errors.append(f"{name.upper()}_INVALID")
            continue
        if not 0.0 <= value <= 100.0:
            errors.append(f"{name.upper()}_OUT_OF_RANGE")

    try:
        portfolio_score = float(payload.get("portfolio_score", 0.0))
        if not 0.0 <= portfolio_score <= 100.0:
            errors.append("PORTFOLIO_SCORE_OUT_OF_RANGE")
    except (TypeError, ValueError):
        errors.append("PORTFOLIO_SCORE_INVALID")
    return errors
