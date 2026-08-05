from __future__ import annotations

from decimal import Decimal

from .base import Strategy
from .indicators import (
    closes,
    highs,
    lows,
    mean,
    rolling_high,
    rolling_low,
    simple_return,
)
from .models import D, HUNDRED, ZERO, clamp, text


def neutral(strategy: str, symbol: str, reason: str) -> dict:
    return {
        "strategy": strategy,
        "symbol": symbol,
        "status": "INSUFFICIENT_DATA",
        "signal": "HOLD",
        "score": "0",
        "confidence": "0",
        "reason": reason,
        "metrics": {},
    }


class MomentumStrategy(Strategy):
    name = "momentum"
    minimum_bars = 6

    def evaluate(self, symbol, bars, config):
        values = closes(bars)
        lookback = int(config.get("lookback", 5))
        if len(values) < max(self.minimum_bars, lookback + 1):
            return neutral(self.name, symbol, "MOMENTUM_BARS_MISSING")
        value = simple_return(values[-lookback - 1], values[-1])
        score = clamp(abs(value) * Decimal("1000"))
        signal = "BUY" if value > 0 else "SELL" if value < 0 else "HOLD"
        return {
            "strategy": self.name,
            "symbol": symbol,
            "status": "PASS",
            "signal": signal,
            "score": text(score),
            "confidence": text(score),
            "reason": "LOOKBACK_RETURN",
            "metrics": {"return_percent": text(value * HUNDRED)},
        }


class MeanReversionStrategy(Strategy):
    name = "mean_reversion"
    minimum_bars = 6

    def evaluate(self, symbol, bars, config):
        values = closes(bars)
        window = int(config.get("window", 5))
        if len(values) < max(self.minimum_bars, window):
            return neutral(self.name, symbol, "MEAN_REVERSION_BARS_MISSING")
        avg = mean(values[-window:])
        last = values[-1]
        deviation = (last - avg) / avg if avg else ZERO
        threshold = D(config.get("threshold_percent", "0.5")) / HUNDRED
        signal = "SELL" if deviation > threshold else "BUY" if deviation < -threshold else "HOLD"
        score = clamp(abs(deviation) * Decimal("1000"))
        return {
            "strategy": self.name,
            "symbol": symbol,
            "status": "PASS",
            "signal": signal,
            "score": text(score),
            "confidence": text(score),
            "reason": "PRICE_VS_ROLLING_MEAN",
            "metrics": {
                "deviation_percent": text(deviation * HUNDRED),
                "rolling_mean": text(avg),
            },
        }


class BreakoutStrategy(Strategy):
    name = "breakout"
    minimum_bars = 6

    def evaluate(self, symbol, bars, config):
        close_values = closes(bars)
        high_values = highs(bars[:-1])
        low_values = lows(bars[:-1])
        window = int(config.get("window", 5))
        if (
            len(close_values) < self.minimum_bars
            or len(high_values) < window
            or len(low_values) < window
        ):
            return neutral(self.name, symbol, "BREAKOUT_BARS_MISSING")
        last = close_values[-1]
        upper = rolling_high(high_values, window)
        lower = rolling_low(low_values, window)
        signal = "BUY" if last > upper else "SELL" if last < lower else "HOLD"
        distance = (
            (last - upper) / upper if signal == "BUY" and upper
            else (lower - last) / lower if signal == "SELL" and lower
            else ZERO
        )
        score = clamp(abs(distance) * Decimal("2000"))
        return {
            "strategy": self.name,
            "symbol": symbol,
            "status": "PASS",
            "signal": signal,
            "score": text(score),
            "confidence": text(score),
            "reason": "RANGE_BREAKOUT",
            "metrics": {
                "previous_high": text(upper),
                "previous_low": text(lower),
                "last_close": text(last),
            },
        }


class TrendStrategy(Strategy):
    name = "trend"
    minimum_bars = 8

    def evaluate(self, symbol, bars, config):
        values = closes(bars)
        fast = int(config.get("fast_window", 3))
        slow = int(config.get("slow_window", 7))
        if len(values) < max(self.minimum_bars, slow):
            return neutral(self.name, symbol, "TREND_BARS_MISSING")
        fast_avg = mean(values[-fast:])
        slow_avg = mean(values[-slow:])
        spread = (fast_avg - slow_avg) / slow_avg if slow_avg else ZERO
        signal = "BUY" if spread > 0 else "SELL" if spread < 0 else "HOLD"
        score = clamp(abs(spread) * Decimal("1500"))
        return {
            "strategy": self.name,
            "symbol": symbol,
            "status": "PASS",
            "signal": signal,
            "score": text(score),
            "confidence": text(score),
            "reason": "FAST_SLOW_MEAN_SPREAD",
            "metrics": {
                "fast_mean": text(fast_avg),
                "slow_mean": text(slow_avg),
                "spread_percent": text(spread * HUNDRED),
            },
        }


class GapStrategy(Strategy):
    name = "gap"
    minimum_bars = 2

    def evaluate(self, symbol, bars, config):
        if len(bars) < self.minimum_bars:
            return neutral(self.name, symbol, "GAP_BARS_MISSING")
        previous_close = D(bars[-2].get("close"))
        current_open = D(bars[-1].get("open"))
        if not previous_close or not current_open:
            return neutral(self.name, symbol, "GAP_PRICE_MISSING")
        gap = (current_open - previous_close) / previous_close
        threshold = D(config.get("threshold_percent", "0.5")) / HUNDRED
        signal = "BUY" if gap > threshold else "SELL" if gap < -threshold else "HOLD"
        score = clamp(abs(gap) * Decimal("1000"))
        return {
            "strategy": self.name,
            "symbol": symbol,
            "status": "PASS",
            "signal": signal,
            "score": text(score),
            "confidence": text(score),
            "reason": "OPEN_VS_PREVIOUS_CLOSE",
            "metrics": {"gap_percent": text(gap * HUNDRED)},
        }


STRATEGY_TYPES = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "trend": TrendStrategy,
    "gap": GapStrategy,
}
