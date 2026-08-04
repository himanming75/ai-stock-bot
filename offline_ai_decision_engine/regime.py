from __future__ import annotations
from .models import MarketInput


def classify(value: MarketInput) -> str:
    trend_gap = (value.sma_fast - value.sma_slow) / value.sma_slow
    if value.atr_pct >= 0.04:
        return "HIGH_VOLATILITY"
    if trend_gap >= 0.01 and value.market_trend >= 0:
        return "BULL_TREND"
    if trend_gap <= -0.01 and value.market_trend <= 0:
        return "BEAR_TREND"
    return "RANGE"
