from __future__ import annotations
from statistics import mean

from .math_utils import clamp, ema, ema_series, returns, rolling_std, safe_float, sma


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    changes = [b - a for a, b in zip(closes, closes[1:])]
    sample = changes[-period:]
    gains = [max(x, 0.0) for x in sample]
    losses = [max(-x, 0.0) for x in sample]
    avg_gain = mean(gains)
    avg_loss = mean(losses)
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(closes: list[float], fast=12, slow=26, signal=9) -> dict:
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "histogram": None}
    fast_series = ema_series(closes, fast)
    slow_series = ema_series(closes, slow)
    macd_series = [a - b for a, b in zip(fast_series, slow_series)]
    signal_series = ema_series(macd_series, signal)
    line = macd_series[-1]
    sig = signal_series[-1]
    return {"macd": line, "signal": sig, "histogram": line - sig}


def true_ranges(highs, lows, closes) -> list[float]:
    if not closes:
        return []
    result = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        result.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    return result


def atr(highs, lows, closes, period=14) -> float | None:
    ranges = true_ranges(highs, lows, closes)
    return sma(ranges, period)


def bollinger(closes, period=20, deviations=2.0) -> dict:
    middle = sma(closes, period)
    std = rolling_std(closes, period)
    if middle is None or std is None:
        return {"middle": None, "upper": None, "lower": None, "width": None, "percent_b": None}
    upper = middle + deviations * std
    lower = middle - deviations * std
    width = (upper - lower) / middle if middle else 0.0
    percent_b = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
    return {"middle": middle, "upper": upper, "lower": lower, "width": width, "percent_b": percent_b}


def vwap(highs, lows, closes, volumes) -> float | None:
    total_volume = sum(volumes)
    if not volumes or total_volume <= 0:
        return None
    typical = [(h + l + c) / 3.0 for h, l, c in zip(highs, lows, closes)]
    return sum(p * v for p, v in zip(typical, volumes)) / total_volume


def obv(closes, volumes) -> float:
    value = 0.0
    for previous, current, volume in zip(closes, closes[1:], volumes[1:]):
        if current > previous:
            value += volume
        elif current < previous:
            value -= volume
    return value


def adx(highs, lows, closes, period=14) -> dict:
    if len(closes) < period + 1:
        return {"adx": None, "plus_di": None, "minus_di": None}
    tr = true_ranges(highs, lows, closes)[-period:]
    plus_dm = []
    minus_dm = []
    for i in range(len(closes) - period, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    atr_sum = sum(tr)
    if atr_sum == 0:
        return {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0}
    plus_di = 100.0 * sum(plus_dm) / atr_sum
    minus_di = 100.0 * sum(minus_dm) / atr_sum
    denominator = plus_di + minus_di
    dx = 100.0 * abs(plus_di - minus_di) / denominator if denominator else 0.0
    return {"adx": dx, "plus_di": plus_di, "minus_di": minus_di}


def roc(closes, period=10) -> float | None:
    if len(closes) <= period or closes[-period - 1] == 0:
        return None
    return closes[-1] / closes[-period - 1] - 1.0


def stochastic(highs, lows, closes, period=14) -> float | None:
    if len(closes) < period:
        return None
    high = max(highs[-period:])
    low = min(lows[-period:])
    return 100.0 * (closes[-1] - low) / (high - low) if high != low else 50.0


def feature_record(symbol: str, bars: list[dict]) -> dict:
    bars = sorted(bars, key=lambda x: str(x.get("t", "")))
    opens = [safe_float(x.get("o")) for x in bars]
    highs = [safe_float(x.get("h")) for x in bars]
    lows = [safe_float(x.get("l")) for x in bars]
    closes = [safe_float(x.get("c")) for x in bars]
    volumes = [safe_float(x.get("v")) for x in bars]
    rets = returns(closes)
    macd_values = macd(closes)
    bb = bollinger(closes)
    adx_values = adx(highs, lows, closes)
    current_atr = atr(highs, lows, closes)
    current_vwap = vwap(highs, lows, closes, volumes)
    sma_5 = sma(closes, 5)
    sma_10 = sma(closes, 10)
    sma_20 = sma(closes, 20)
    ema_9 = ema(closes, 9)
    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)
    last = closes[-1]
    volume_mean = mean(volumes[-20:]) if len(volumes) >= 20 else mean(volumes)
    gap = opens[-1] / closes[-2] - 1.0 if len(closes) >= 2 and closes[-2] else 0.0

    return {
        "symbol": symbol,
        "timestamp": bars[-1].get("t"),
        "bar_count": len(bars),
        "open": opens[-1],
        "high": highs[-1],
        "low": lows[-1],
        "close": last,
        "volume": volumes[-1],
        "sma_5": sma_5,
        "sma_10": sma_10,
        "sma_20": sma_20,
        "ema_9": ema_9,
        "ema_12": ema_12,
        "ema_26": ema_26,
        "rsi_14": rsi(closes),
        "macd": macd_values["macd"],
        "macd_signal": macd_values["signal"],
        "macd_histogram": macd_values["histogram"],
        "atr_14": current_atr,
        "atr_percent": current_atr / last if current_atr is not None and last else None,
        "bollinger_middle": bb["middle"],
        "bollinger_upper": bb["upper"],
        "bollinger_lower": bb["lower"],
        "bollinger_width": bb["width"],
        "bollinger_percent_b": bb["percent_b"],
        "vwap": current_vwap,
        "price_vs_vwap": last / current_vwap - 1.0 if current_vwap else None,
        "obv": obv(closes, volumes),
        "adx_14": adx_values["adx"],
        "plus_di_14": adx_values["plus_di"],
        "minus_di_14": adx_values["minus_di"],
        "roc_5": roc(closes, 5),
        "roc_10": roc(closes, 10),
        "stochastic_14": stochastic(highs, lows, closes),
        "return_1": rets[-1] if rets else None,
        "return_5": closes[-1] / closes[-6] - 1.0 if len(closes) >= 6 and closes[-6] else None,
        "return_10": closes[-1] / closes[-11] - 1.0 if len(closes) >= 11 and closes[-11] else None,
        "realized_volatility_20": rolling_std(rets, 20),
        "volume_ratio_20": volumes[-1] / volume_mean if volume_mean else None,
        "gap_return": gap,
        "range_percent": (highs[-1] - lows[-1]) / last if last else None,
        "trend_5_20": sma_5 / sma_20 - 1.0 if sma_5 and sma_20 else None,
        "trend_10_20": sma_10 / sma_20 - 1.0 if sma_10 and sma_20 else None,
    }
