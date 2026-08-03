from __future__ import annotations
from typing import Any

def classify_regime(features: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    trend = float(features.get("trend_slope_pct", 0.0))
    momentum = float(features.get("momentum_pct", 0.0))
    vol = float(features.get("annualized_volatility_pct", 0.0))
    atr = float(features.get("atr_pct", 0.0))
    price_above_long = bool(features.get("price_above_long_sma", False))

    bull_threshold = float(policy.get("bull_trend_threshold_pct", 3.0))
    bear_threshold = float(policy.get("bear_trend_threshold_pct", -3.0))
    high_vol_threshold = float(policy.get("high_volatility_threshold_pct", 35.0))
    low_vol_threshold = float(policy.get("low_volatility_threshold_pct", 12.0))
    high_atr_threshold = float(policy.get("high_atr_threshold_pct", 2.5))

    if trend >= bull_threshold and momentum > 0 and price_above_long:
        primary = "BULL"
    elif trend <= bear_threshold and momentum < 0 and not price_above_long:
        primary = "BEAR"
    else:
        primary = "SIDEWAYS"

    if vol >= high_vol_threshold or atr >= high_atr_threshold:
        volatility_regime = "HIGH_VOLATILITY"
    elif vol <= low_vol_threshold:
        volatility_regime = "LOW_VOLATILITY"
    else:
        volatility_regime = "NORMAL_VOLATILITY"

    risk_mode = (
        "RISK_OFF"
        if primary == "BEAR" or volatility_regime == "HIGH_VOLATILITY"
        else "RISK_ON"
    )

    confidence = 50.0
    confidence += min(25.0, abs(trend) * 2.0)
    confidence += min(15.0, abs(momentum))
    if volatility_regime != "NORMAL_VOLATILITY":
        confidence += 5.0
    confidence = max(0.0, min(100.0, confidence))

    return {
        "primary_regime": primary,
        "volatility_regime": volatility_regime,
        "risk_mode": risk_mode,
        "confidence_score": round(confidence, 2),
    }
