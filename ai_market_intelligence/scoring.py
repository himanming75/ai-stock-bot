from __future__ import annotations
from .math_utils import clamp


def _value(record, key, default=0.0):
    value = record.get(key)
    return default if value is None else float(value)


def score_record(record: dict) -> dict:
    trend = clamp(_value(record, "trend_5_20") * 1000.0, -25.0, 25.0)
    momentum = clamp(_value(record, "roc_10") * 500.0, -25.0, 25.0)
    macd = clamp(_value(record, "macd_histogram") / max(abs(_value(record, "close", 1.0)), 1e-9) * 10000.0, -15.0, 15.0)
    rsi = _value(record, "rsi_14", 50.0)
    rsi_score = clamp((rsi - 50.0) * 0.4, -15.0, 15.0)
    volume = clamp((_value(record, "volume_ratio_20", 1.0) - 1.0) * 10.0, -10.0, 10.0)
    vwap = clamp(_value(record, "price_vs_vwap") * 500.0, -10.0, 10.0)
    volatility_penalty = clamp(_value(record, "atr_percent") * 1000.0, 0.0, 15.0)

    raw = trend + momentum + macd + rsi_score + volume + vwap - volatility_penalty
    score = clamp(raw, -100.0, 100.0)
    confidence = clamp(
        40.0
        + abs(score) * 0.45
        + min(_value(record, "bar_count") / 2.0, 20.0),
        0.0,
        100.0,
    )
    if score >= 25:
        signal = "BULLISH"
    elif score <= -25:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    return {
        **record,
        "technical_score": round(score, 6),
        "confidence": round(confidence, 6),
        "signal": signal,
        "score_components": {
            "trend": trend,
            "momentum": momentum,
            "macd": macd,
            "rsi": rsi_score,
            "volume": volume,
            "vwap": vwap,
            "volatility_penalty": volatility_penalty,
        },
    }


def market_regime(scored: list[dict]) -> dict:
    if not scored:
        return {"regime": "UNKNOWN", "breadth": 0.0, "average_score": 0.0}
    average = sum(x["technical_score"] for x in scored) / len(scored)
    bullish = sum(1 for x in scored if x["signal"] == "BULLISH")
    bearish = sum(1 for x in scored if x["signal"] == "BEARISH")
    breadth = (bullish - bearish) / len(scored)
    average_vol = sum(float(x.get("atr_percent") or 0.0) for x in scored) / len(scored)
    if average_vol > 0.035:
        regime = "HIGH_VOLATILITY"
    elif average >= 20 and breadth >= 0:
        regime = "BULL_TREND"
    elif average <= -20 and breadth <= 0:
        regime = "BEAR_TREND"
    else:
        regime = "SIDEWAYS_OR_MIXED"
    return {
        "regime": regime,
        "breadth": round(breadth, 6),
        "average_score": round(average, 6),
        "average_atr_percent": round(average_vol, 8),
    }
