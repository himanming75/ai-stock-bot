from __future__ import annotations
from .models import MarketInput


def validate(value: MarketInput) -> list[str]:
    errors: list[str] = []
    if not value.symbol:
        errors.append("SYMBOL_REQUIRED")
    for name in ("close", "sma_fast", "sma_slow"):
        if getattr(value, name) <= 0:
            errors.append(f"{name.upper()}_MUST_BE_POSITIVE")
    if not 0 <= value.rsi <= 100:
        errors.append("RSI_OUT_OF_RANGE")
    if value.atr_pct < 0:
        errors.append("ATR_PCT_OUT_OF_RANGE")
    if value.volume_ratio < 0:
        errors.append("VOLUME_RATIO_OUT_OF_RANGE")
    if not -1 <= value.market_trend <= 1:
        errors.append("MARKET_TREND_OUT_OF_RANGE")
    if not -1 <= value.news_score <= 1:
        errors.append("NEWS_SCORE_OUT_OF_RANGE")
    return errors
