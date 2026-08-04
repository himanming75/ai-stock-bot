from __future__ import annotations
from .indicators import atr_pct, ema, macd_histogram, rsi, volume_ratio
from .models import Bar


def calculate(bars: list[Bar], market_trend: float, news_score: float) -> dict[str, float]:
    closes = [bar.close for bar in bars]
    ema_fast = ema(closes, 12)
    ema_slow = ema(closes, 26)
    trend = max(-1.0, min(1.0, ((ema_fast - ema_slow) / ema_slow) * 30.0))
    momentum = max(-1.0, min(1.0, (rsi(closes) - 50.0) / 30.0))
    macd = max(-1.0, min(1.0, macd_histogram(closes) * 100.0))
    volume = max(-1.0, min(1.0, volume_ratio(bars) - 1.0))
    volatility = max(0.0, min(1.0, atr_pct(bars) / 0.05))
    return {
        "trend": round(trend, 6),
        "momentum": round(momentum, 6),
        "macd": round(macd, 6),
        "volume": round(volume, 6),
        "market_trend": round(max(-1.0, min(1.0, market_trend)), 6),
        "news": round(max(-1.0, min(1.0, news_score)), 6),
        "volatility": round(volatility, 6),
        "rsi": round(rsi(closes), 4),
        "atr_pct": round(atr_pct(bars), 6),
        "volume_ratio": round(volume_ratio(bars), 6),
    }
