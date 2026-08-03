from __future__ import annotations
from typing import Any

from market_regime_engine.indicators import (
    sma,
    annualized_volatility,
    momentum,
    average_true_range_pct,
    trend_slope_pct,
)
from market_regime_engine.classifier import classify_regime

def analyze_frame(
    bars: list[dict[str, Any]],
    policy: dict[str, Any],
    frame_name: str,
) -> dict[str, Any]:
    closes = [float(row["close"]) for row in bars]
    short_period = min(
        int(policy.get("short_sma_period", 10)),
        max(2, len(closes) // 4),
    )
    long_period = min(
        int(policy.get("long_sma_period", 25)),
        max(short_period + 1, len(closes) // 2),
    )
    momentum_period = min(
        int(policy.get("momentum_period", 10)),
        max(2, len(closes) // 4),
    )
    slope_period = min(
        int(policy.get("trend_slope_period", 15)),
        max(3, len(closes) // 3),
    )

    short_value = sma(closes, short_period)
    long_value = sma(closes, long_period)
    latest = closes[-1] if closes else 0.0

    features = {
        "frame_name": frame_name,
        "bar_count": len(bars),
        "latest_close": round(latest, 4),
        "short_sma": round(short_value, 4) if short_value is not None else None,
        "long_sma": round(long_value, 4) if long_value is not None else None,
        "price_above_short_sma": latest > short_value if short_value is not None else False,
        "price_above_long_sma": latest > long_value if long_value is not None else False,
        "momentum_pct": round(momentum(closes, momentum_period), 4),
        "trend_slope_pct": round(trend_slope_pct(closes, slope_period), 4),
        "annualized_volatility_pct": round(annualized_volatility(closes), 4),
        "atr_pct": round(average_true_range_pct(bars, min(14, max(2, len(bars)-1))), 4),
    }
    regime = classify_regime(features, policy)
    return {
        "frame_name": frame_name,
        "features": features,
        "regime": regime,
    }
