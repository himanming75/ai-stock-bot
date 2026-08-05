from __future__ import annotations
from .utils import clamp, signal, val

def momentum(record):
    score = (
        val(record, "roc_5") * 550
        + val(record, "roc_10") * 350
        + val(record, "return_5") * 350
        + val(record, "macd_histogram") / max(abs(val(record, "close", 1)), 1e-9) * 7000
    )
    score = clamp(score)
    return {"name": "MOMENTUM", "score": score, "signal": signal(score)}

def trend_following(record):
    adx = val(record, "adx_14")
    direction = 1.0 if val(record, "plus_di_14") >= val(record, "minus_di_14") else -1.0
    score = (
        val(record, "trend_5_20") * 900
        + val(record, "trend_10_20") * 700
        + direction * max(adx - 15.0, 0.0) * 1.2
        + val(record, "price_vs_vwap") * 350
    )
    score = clamp(score)
    return {"name": "TREND_FOLLOWING", "score": score, "signal": signal(score)}

def mean_reversion(record):
    rsi = val(record, "rsi_14", 50)
    percent_b = val(record, "bollinger_percent_b", 0.5)
    stochastic = val(record, "stochastic_14", 50)
    score = (
        (50.0 - rsi) * 1.2
        + (0.5 - percent_b) * 70
        + (50.0 - stochastic) * 0.55
        - val(record, "roc_5") * 250
    )
    score = clamp(score)
    return {"name": "MEAN_REVERSION", "score": score, "signal": signal(score)}

def breakout(record):
    percent_b = val(record, "bollinger_percent_b", 0.5)
    volume = val(record, "volume_ratio_20", 1.0)
    range_percent = val(record, "range_percent")
    score = (
        (percent_b - 0.5) * 90
        + (volume - 1.0) * 25
        + val(record, "roc_5") * 300
        + range_percent * 300
    )
    score = clamp(score)
    return {"name": "BREAKOUT", "score": score, "signal": signal(score)}

def vwap_strategy(record):
    score = (
        val(record, "price_vs_vwap") * 700
        + val(record, "volume_ratio_20", 1.0) * 4
        + val(record, "return_1") * 250
    )
    score = clamp(score)
    return {"name": "VWAP_MOMENTUM", "score": score, "signal": signal(score)}

def volatility_strategy(record):
    atr_percent = val(record, "atr_percent")
    width = val(record, "bollinger_width")
    momentum_direction = 1.0 if val(record, "roc_5") >= 0 else -1.0
    score = momentum_direction * (
        min(atr_percent * 900, 35)
        + min(width * 180, 35)
        + max(val(record, "adx_14") - 20, 0)
    )
    score = clamp(score)
    return {"name": "VOLATILITY_EXPANSION", "score": score, "signal": signal(score)}

STRATEGIES = (
    momentum,
    trend_following,
    mean_reversion,
    breakout,
    vwap_strategy,
    volatility_strategy,
)
