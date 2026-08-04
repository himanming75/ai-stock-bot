from __future__ import annotations
from .models import MarketInput


def build(value: MarketInput) -> dict[str, float]:
    trend = (value.sma_fast - value.sma_slow) / value.sma_slow
    price_extension = (value.close - value.sma_fast) / value.sma_fast
    rsi_centered = (value.rsi - 50.0) / 50.0
    volume_strength = max(-1.0, min(1.0, value.volume_ratio - 1.0))
    volatility_penalty = min(1.0, value.atr_pct / 0.05)
    return {
        "trend": max(-1.0, min(1.0, trend * 20.0)),
        "price_extension": max(-1.0, min(1.0, price_extension * 10.0)),
        "rsi_centered": max(-1.0, min(1.0, rsi_centered)),
        "volume_strength": volume_strength,
        "volatility_penalty": volatility_penalty,
        "market_trend": value.market_trend,
        "news_score": value.news_score,
    }
