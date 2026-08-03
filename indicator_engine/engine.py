from __future__ import annotations

from typing import Any

from indicator_engine.calculations import (
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    vwap,
)
from indicator_engine.models import Bar
from indicator_engine.signals import build_strategy_signals


def evaluate_indicators(symbol: str, bars: list[Bar]) -> dict[str, Any]:
    if not bars:
        raise ValueError("at least one OHLCV bar is required")

    for bar in bars:
        bar.validate()

    closes = [bar.close for bar in bars]
    macd_values = macd(closes)
    bands = bollinger_bands(closes)

    indicators = {
        "symbol": symbol.upper().strip() or "UNKNOWN",
        "bar_count": len(bars),
        "latest_timestamp": bars[-1].timestamp,
        "close": bars[-1].close,
        "sma_20": sma(closes, 20),
        "sma_50": sma(closes, 50),
        "ema_20": ema(closes, 20),
        "ema_50": ema(closes, 50),
        "ema_200": ema(closes, 200),
        "rsi_14": rsi(closes, 14),
        "macd": macd_values["macd"],
        "macd_signal": macd_values["signal"],
        "macd_histogram": macd_values["histogram"],
        "atr_14": atr(bars, 14),
        "bollinger_upper": bands["upper"],
        "bollinger_middle": bands["middle"],
        "bollinger_lower": bands["lower"],
        "bollinger_width_pct": bands["width_pct"],
        "vwap": vwap(bars),
    }
    indicators["strategy_signals"] = build_strategy_signals(indicators)
    indicators["indicator_count"] = sum(
        1 for key, value in indicators.items()
        if key not in {"symbol", "bar_count", "latest_timestamp", "strategy_signals"}
        and value is not None
    )
    return indicators
