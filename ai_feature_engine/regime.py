from __future__ import annotations


def classify_regime(features: dict) -> dict:
    atr_percent = float(features.get("atr_percent") or 0)
    width = float(features.get("bollinger_width") or 0)
    ema9 = features.get("ema9")
    ema21 = features.get("ema21")
    close = float(features.get("close") or 0)

    trend_strength = 0.0
    if ema9 is not None and ema21 is not None and close:
        trend_strength = abs(ema9 - ema21) / close

    if atr_percent >= 0.03 or width >= 0.08:
        regime = "REGIME_VOLATILE"
    elif trend_strength >= 0.01:
        regime = "REGIME_TRENDING"
    else:
        regime = "REGIME_RANGE"

    if ema9 is None or ema21 is None:
        trend = "TREND_SIDEWAYS"
    elif ema9 > ema21:
        trend = "TREND_UP"
    elif ema9 < ema21:
        trend = "TREND_DOWN"
    else:
        trend = "TREND_SIDEWAYS"

    return {
        "regime": regime,
        "trend": trend,
        "trend_strength": trend_strength,
    }
