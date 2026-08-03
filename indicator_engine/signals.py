from __future__ import annotations

from typing import Any


def clamp(value: float) -> float:
    return max(-100.0, min(100.0, value))


def build_strategy_signals(indicators: dict[str, Any]) -> list[dict[str, Any]]:
    close = float(indicators["close"])
    output: list[dict[str, Any]] = []

    rsi_value = indicators.get("rsi_14")
    if rsi_value is not None:
        score = (50.0 - float(rsi_value)) * 2.0
        output.append({
            "name": "RSI",
            "score": clamp(score),
            "weight": 1.0,
            "enabled": True,
            "reason": f"RSI(14)={float(rsi_value):.2f}",
        })

    histogram = indicators.get("macd_histogram")
    if histogram is not None:
        normalizer = max(abs(close) * 0.005, 0.000001)
        score = float(histogram) / normalizer * 50.0
        output.append({
            "name": "MACD",
            "score": clamp(score),
            "weight": 1.2,
            "enabled": True,
            "reason": f"MACD histogram={float(histogram):.6f}",
        })

    ema20 = indicators.get("ema_20")
    ema50 = indicators.get("ema_50")
    if ema20 is not None and ema50 is not None:
        spread_pct = ((float(ema20) - float(ema50)) / close) * 100.0
        output.append({
            "name": "EMA_TREND",
            "score": clamp(spread_pct * 20.0),
            "weight": 1.0,
            "enabled": True,
            "reason": f"EMA20/EMA50 spread={spread_pct:.3f}%",
        })

    current_vwap = indicators.get("vwap")
    if current_vwap is not None:
        deviation_pct = ((close - float(current_vwap)) / float(current_vwap)) * 100.0
        output.append({
            "name": "VWAP",
            "score": clamp(deviation_pct * 15.0),
            "weight": 0.8,
            "enabled": True,
            "reason": f"Close/VWAP deviation={deviation_pct:.3f}%",
        })

    upper = indicators.get("bollinger_upper")
    lower = indicators.get("bollinger_lower")
    if upper is not None and lower is not None and upper != lower:
        position = (close - float(lower)) / (float(upper) - float(lower))
        mean_reversion_score = (0.5 - position) * 100.0
        output.append({
            "name": "BOLLINGER",
            "score": clamp(mean_reversion_score),
            "weight": 0.7,
            "enabled": True,
            "reason": f"Bollinger position={position:.3f}",
        })

    return output
