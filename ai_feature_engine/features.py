from __future__ import annotations
from .indicators import (
    atr,
    bollinger,
    ema,
    macd,
    rsi,
    vwap,
)
from .models import Bar


def build_features(bars: list[Bar]) -> dict:
    closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    rsi14 = rsi(closes, 14)
    macd_values = macd(closes)
    atr14 = atr(bars, 14)
    boll = bollinger(closes, 20, 2.0)
    vwap_values = vwap(bars)

    last = len(bars) - 1
    previous = max(0, last - 5)
    momentum_5 = 0.0 if closes[previous] == 0 else (
        closes[last] / closes[previous] - 1
    )
    volume_avg = sum(volumes[-20:]) / min(20, len(volumes))
    volume_ratio = 0.0 if volume_avg == 0 else volumes[-1] / volume_avg
    atr_percent = 0.0 if closes[-1] == 0 or atr14[-1] is None else atr14[-1] / closes[-1]

    return {
        "close": closes[-1],
        "ema9": ema9[-1],
        "ema21": ema21[-1],
        "rsi14": rsi14[-1],
        "macd": macd_values["line"][-1],
        "macd_signal": macd_values["signal"][-1],
        "macd_histogram": macd_values["histogram"][-1],
        "vwap": vwap_values[-1],
        "atr14": atr14[-1],
        "atr_percent": atr_percent,
        "bollinger_middle": boll["middle"][-1],
        "bollinger_upper": boll["upper"][-1],
        "bollinger_lower": boll["lower"][-1],
        "bollinger_width": boll["width"][-1],
        "momentum_5": momentum_5,
        "volume_ratio": volume_ratio,
    }
