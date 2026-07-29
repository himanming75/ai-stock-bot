"""V25.1 Offline Multi-Indicator Signal Engine.

Deterministic analysis of caller-supplied OHLCV bars only. This module never
fetches market data, accesses accounts, calls brokers, creates/submits orders,
reserves funds/holdings, or authorizes live execution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

VERSION = "25.1"
ENGINE_NAME = "offline-multi-indicator-signal-engine"

FORBIDDEN_CAPABILITIES = {
    "market_data_api": False,
    "account_api": False,
    "network_access": False,
    "broker_api": False,
    "order_creation": False,
    "order_submission": False,
    "live_execution": False,
    "fund_reservation": False,
    "holding_reservation": False,
}


class SignalAction(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MultiSignalPolicy:
    fast_ema: int = 12
    slow_ema: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    atr_period: int = 14
    bollinger_period: int = 20
    bollinger_stddev: float = 2.0
    stochastic_period: int = 14
    stochastic_smooth: int = 3
    buy_threshold: float = 0.30
    sell_threshold: float = -0.30
    min_bars: int = 60
    max_atr_ratio: float = 0.12
    max_abs_return: float = 0.35
    min_volume: float = 0.0
    minimum_consensus: int = 3

    def validate(self) -> None:
        ints = {
            "fast_ema": self.fast_ema, "slow_ema": self.slow_ema,
            "macd_signal": self.macd_signal, "rsi_period": self.rsi_period,
            "atr_period": self.atr_period, "bollinger_period": self.bollinger_period,
            "stochastic_period": self.stochastic_period,
            "stochastic_smooth": self.stochastic_smooth, "min_bars": self.min_bars,
            "minimum_consensus": self.minimum_consensus,
        }
        for name, value in ints.items():
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.fast_ema >= self.slow_ema:
            raise ValueError("fast_ema must be smaller than slow_ema")
        required = max(self.slow_ema + self.macd_signal, self.rsi_period + 1,
                       self.atr_period + 1, self.bollinger_period,
                       self.stochastic_period + self.stochastic_smooth)
        if self.min_bars < required:
            raise ValueError("min_bars is too small for configured indicators")
        if not 0.0 < self.bollinger_stddev <= 10.0:
            raise ValueError("bollinger_stddev must be in (0, 10]")
        if not -1.0 <= self.sell_threshold < self.buy_threshold <= 1.0:
            raise ValueError("thresholds must satisfy -1 <= sell < buy <= 1")
        if not 0.0 < self.max_atr_ratio <= 1.0:
            raise ValueError("max_atr_ratio must be in (0, 1]")
        if not 0.0 < self.max_abs_return <= 5.0:
            raise ValueError("max_abs_return must be in (0, 5]")
        if self.min_volume < 0:
            raise ValueError("min_volume cannot be negative")
        if self.minimum_consensus > 6:
            raise ValueError("minimum_consensus cannot exceed 6")


@dataclass(frozen=True)
class IndicatorSnapshot:
    close: float
    ema_fast: float
    ema_slow: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    atr: float
    atr_ratio: float
    bollinger_lower: float
    bollinger_middle: float
    bollinger_upper: float
    bollinger_position: float
    stochastic_k: float
    stochastic_d: float
    obv: float
    obv_slope: float
    latest_return: float
    volume: float


@dataclass(frozen=True)
class ComponentScores:
    trend: float
    momentum: float
    macd: float
    bollinger: float
    stochastic: float
    volume_flow: float
    volatility_gate: float
    volume_gate: float


@dataclass(frozen=True)
class ConsensusSnapshot:
    bullish_votes: int
    bearish_votes: int
    neutral_votes: int
    required_votes: int
    direction: str


@dataclass(frozen=True)
class MultiSignalResult:
    version: str
    engine: str
    symbol: str
    action: str
    score: float
    confidence: float
    reason: str
    bars_used: int
    evaluated_at: str
    indicators: IndicatorSnapshot
    components: ComponentScores
    consensus: ConsensusSnapshot
    input_hash: str
    policy_hash: str
    result_hash: str
    offline_only: bool
    broker_blocked: bool
    live_execution_blocked: bool


class OfflineMultiSignalEngine:
    def __init__(self, policy: MultiSignalPolicy | None = None) -> None:
        self.policy = policy or MultiSignalPolicy()
        self.policy.validate()

    def evaluate(self, symbol: str, bars: Sequence[PriceBar] | Iterable[PriceBar], *,
                 evaluated_at: str | None = None) -> MultiSignalResult:
        symbol = _validate_symbol(symbol)
        bars = tuple(bars)
        _validate_bars(bars, self.policy.min_bars)
        closes = [b.close for b in bars]
        highs = [b.high for b in bars]
        lows = [b.low for b in bars]
        volumes = [b.volume for b in bars]

        ema_fast_s = _ema_series(closes, self.policy.fast_ema)
        ema_slow_s = _ema_series(closes, self.policy.slow_ema)
        macd_s = [a - b for a, b in zip(ema_fast_s, ema_slow_s)]
        macd_sig_s = _ema_series(macd_s, self.policy.macd_signal)
        rsi = _rsi(closes, self.policy.rsi_period)
        atr = _atr(highs, lows, closes, self.policy.atr_period)
        middle = _sma(closes, self.policy.bollinger_period)
        std = _stddev(closes[-self.policy.bollinger_period:])
        lower = middle - self.policy.bollinger_stddev * std
        upper = middle + self.policy.bollinger_stddev * std
        band_width = max(upper - lower, 1e-12)
        band_position = _clip((closes[-1] - lower) / band_width, 0.0, 1.0)
        k_series = _stochastic_k_series(highs, lows, closes, self.policy.stochastic_period)
        d = _sma(k_series, min(self.policy.stochastic_smooth, len(k_series)))
        k = k_series[-1]
        obv_series = _obv_series(closes, volumes)
        obv_window = obv_series[-min(10, len(obv_series)):]
        obv_scale = max(sum(abs(v) for v in volumes[-min(10, len(volumes)):]), 1.0)
        obv_slope = (obv_window[-1] - obv_window[0]) / obv_scale
        latest_return = closes[-1] / closes[-2] - 1.0
        atr_ratio = atr / closes[-1]

        trend = _clip((ema_fast_s[-1] / ema_slow_s[-1] - 1.0) * 25.0)
        momentum = _clip((rsi - 50.0) / 25.0)
        macd = _clip((macd_s[-1] - macd_sig_s[-1]) / max(closes[-1] * 0.01, 1e-12))
        bollinger = _clip((band_position - 0.5) * 2.0)
        stochastic = _clip((k - 50.0) / 50.0)
        volume_flow = _clip(obv_slope * 5.0)
        volatility_gate = _clip(1.0 - atr_ratio / self.policy.max_atr_ratio, 0.0, 1.0)
        volume_gate = 1.0 if volumes[-1] >= self.policy.min_volume else 0.0

        directional = [trend, momentum, macd, bollinger, stochastic, volume_flow]
        bullish = sum(x >= 0.12 for x in directional)
        bearish = sum(x <= -0.12 for x in directional)
        neutral = 6 - bullish - bearish
        if bullish >= self.policy.minimum_consensus and bullish > bearish:
            direction = "BULLISH"
        elif bearish >= self.policy.minimum_consensus and bearish > bullish:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        weighted = (0.24 * trend + 0.18 * momentum + 0.18 * macd +
                    0.14 * bollinger + 0.12 * stochastic + 0.14 * volume_flow)
        score = round(_clip(weighted) * volatility_gate * volume_gate, 6)
        consensus_strength = max(bullish, bearish) / 6.0
        confidence = round(_clip(abs(score) * 0.65 + consensus_strength * 0.25 +
                                 volatility_gate * 0.10, 0.0, 1.0), 6)

        if volume_gate == 0.0:
            action, reason = SignalAction.HOLD, "HOLD: volume is below the offline policy minimum"
        elif abs(latest_return) > self.policy.max_abs_return:
            action, reason = SignalAction.HOLD, "HOLD: abnormal one-bar return triggered the safety guard"
        elif atr_ratio > self.policy.max_atr_ratio:
            action, reason = SignalAction.HOLD, "HOLD: ATR volatility exceeded the offline policy limit"
        elif direction == "BULLISH" and score >= self.policy.buy_threshold:
            action, reason = SignalAction.BUY, "BUY: multi-indicator bullish consensus exceeded the threshold"
        elif direction == "BEARISH" and score <= self.policy.sell_threshold:
            action, reason = SignalAction.SELL, "SELL: multi-indicator bearish consensus crossed the threshold"
        else:
            action, reason = SignalAction.HOLD, "HOLD: score or indicator consensus remained insufficient"

        timestamp = evaluated_at or datetime.now(timezone.utc).isoformat()
        _validate_timestamp(timestamp)
        indicators = IndicatorSnapshot(
            round(closes[-1], 8), round(ema_fast_s[-1], 8), round(ema_slow_s[-1], 8),
            round(rsi, 8), round(macd_s[-1], 8), round(macd_sig_s[-1], 8),
            round(macd_s[-1] - macd_sig_s[-1], 8), round(atr, 8), round(atr_ratio, 8),
            round(lower, 8), round(middle, 8), round(upper, 8), round(band_position, 8),
            round(k, 8), round(d, 8), round(obv_series[-1], 8), round(obv_slope, 8),
            round(latest_return, 8), round(volumes[-1], 8))
        components = ComponentScores(*(round(x, 8) for x in
            (trend, momentum, macd, bollinger, stochastic, volume_flow,
             volatility_gate, volume_gate)))
        consensus = ConsensusSnapshot(bullish, bearish, neutral,
                                      self.policy.minimum_consensus, direction)
        input_hash = _hash_json([asdict(b) for b in bars])
        policy_hash = _hash_json(asdict(self.policy))
        hash_payload = {
            "version": VERSION, "engine": ENGINE_NAME, "symbol": symbol,
            "action": action.value, "score": score, "confidence": confidence,
            "reason": reason, "bars_used": len(bars), "evaluated_at": timestamp,
            "indicators": asdict(indicators), "components": asdict(components),
            "consensus": asdict(consensus), "input_hash": input_hash,
            "policy_hash": policy_hash, "offline_only": True,
            "broker_blocked": True, "live_execution_blocked": True,
        }
        return MultiSignalResult(
            version=VERSION, engine=ENGINE_NAME, symbol=symbol, action=action.value,
            score=score, confidence=confidence, reason=reason, bars_used=len(bars),
            evaluated_at=timestamp, indicators=indicators, components=components,
            consensus=consensus, input_hash=input_hash, policy_hash=policy_hash,
            result_hash=_hash_json(hash_payload), offline_only=True,
            broker_blocked=True, live_execution_blocked=True,
        )


def verify_result(result: MultiSignalResult) -> bool:
    data = asdict(result)
    stored = data.pop("result_hash")
    return stored == _hash_json(data)


def save_result(result: MultiSignalResult, path: str | Path) -> None:
    if not verify_result(result):
        raise ValueError("cannot save a result with an invalid hash")
    Path(path).write_text(json.dumps(asdict(result), sort_keys=True, indent=2), encoding="utf-8")


def load_result(path: str | Path) -> MultiSignalResult:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    raw["indicators"] = IndicatorSnapshot(**raw["indicators"])
    raw["components"] = ComponentScores(**raw["components"])
    raw["consensus"] = ConsensusSnapshot(**raw["consensus"])
    result = MultiSignalResult(**raw)
    if not verify_result(result):
        raise ValueError("saved result hash verification failed")
    return result


def _validate_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise TypeError("symbol must be a string")
    value = symbol.strip().upper()
    if not value or len(value) > 15 or not all(c.isalnum() or c in ".-_" for c in value):
        raise ValueError("symbol must contain 1-15 safe characters")
    return value


def _validate_bars(bars: tuple[PriceBar, ...], minimum: int) -> None:
    if len(bars) < minimum:
        raise ValueError(f"at least {minimum} bars are required")
    previous = None
    for i, bar in enumerate(bars):
        if not isinstance(bar, PriceBar):
            raise TypeError(f"bar {i} must be PriceBar")
        _validate_timestamp(bar.timestamp)
        values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError(f"bar {i} contains a non-finite number")
        if min(bar.open, bar.high, bar.low, bar.close) <= 0 or bar.volume < 0:
            raise ValueError(f"bar {i} contains invalid price or volume")
        if bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close) or bar.high < bar.low:
            raise ValueError(f"bar {i} has inconsistent OHLC values")
        dt = datetime.fromisoformat(bar.timestamp.replace("Z", "+00:00"))
        if previous is not None and dt <= previous:
            raise ValueError("bar timestamps must be strictly increasing")
        previous = dt


def _validate_timestamp(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("timestamp must be a string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must include timezone information")


def _sma(values: Sequence[float], period: int) -> float:
    if len(values) < period:
        raise ValueError("insufficient values for SMA")
    return sum(values[-period:]) / period


def _ema_series(values: Sequence[float], period: int) -> list[float]:
    if not values:
        raise ValueError("EMA values cannot be empty")
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * value + (1.0 - alpha) * out[-1])
    return out


def _rsi(closes: Sequence[float], period: int) -> float:
    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(x, 0.0) for x in changes]
    losses = [max(-x, 0.0) for x in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def _atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> float:
    trs = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def _stddev(values: Sequence[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def _stochastic_k_series(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int) -> list[float]:
    result = []
    for i in range(period - 1, len(closes)):
        hi = max(highs[i-period+1:i+1]); lo = min(lows[i-period+1:i+1])
        result.append(50.0 if hi == lo else 100.0 * (closes[i] - lo) / (hi - lo))
    return result


def _obv_series(closes: Sequence[float], volumes: Sequence[float]) -> list[float]:
    out = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]: out.append(out[-1] + volumes[i])
        elif closes[i] < closes[i-1]: out.append(out[-1] - volumes[i])
        else: out.append(out[-1])
    return out


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _hash_json(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
