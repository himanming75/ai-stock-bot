"""V25.0 Offline AI Signal Engine.

Deterministic, offline-only signal generation from caller-supplied OHLCV bars.
This module never downloads market data, accesses accounts, calls brokers,
creates orders, submits orders, reserves funds/holdings, or authorizes live execution.
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

VERSION = "25.0"
ENGINE_NAME = "offline-ai-signal-engine"

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
class SignalPolicy:
    fast_sma: int = 5
    slow_sma: int = 20
    rsi_period: int = 14
    ema_fast: int = 12
    ema_slow: int = 26
    ema_signal: int = 9
    buy_threshold: float = 0.35
    sell_threshold: float = -0.35
    min_bars: int = 40
    max_abs_return: float = 0.40
    min_volume: float = 0.0

    def validate(self) -> None:
        integer_fields = {
            "fast_sma": self.fast_sma,
            "slow_sma": self.slow_sma,
            "rsi_period": self.rsi_period,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "ema_signal": self.ema_signal,
            "min_bars": self.min_bars,
        }
        for name, value in integer_fields.items():
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.fast_sma >= self.slow_sma:
            raise ValueError("fast_sma must be smaller than slow_sma")
        if self.ema_fast >= self.ema_slow:
            raise ValueError("ema_fast must be smaller than ema_slow")
        if not -1.0 <= self.sell_threshold < self.buy_threshold <= 1.0:
            raise ValueError("thresholds must satisfy -1 <= sell < buy <= 1")
        if not 0.0 < self.max_abs_return <= 5.0:
            raise ValueError("max_abs_return must be in (0, 5]")
        if self.min_volume < 0:
            raise ValueError("min_volume cannot be negative")


@dataclass(frozen=True)
class IndicatorSnapshot:
    close: float
    fast_sma: float
    slow_sma: float
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    latest_return: float
    volume: float


@dataclass(frozen=True)
class SignalComponents:
    trend: float
    momentum: float
    macd: float
    stability: float
    volume_gate: float


@dataclass(frozen=True)
class OfflineSignalResult:
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
    components: SignalComponents
    input_hash: str
    policy_hash: str
    result_hash: str
    offline_only: bool
    broker_blocked: bool
    live_execution_blocked: bool


class OfflineSignalEngine:
    def __init__(self, policy: SignalPolicy | None = None) -> None:
        self.policy = policy or SignalPolicy()
        self.policy.validate()

    def evaluate(
        self,
        symbol: str,
        bars: Sequence[PriceBar] | Iterable[PriceBar],
        *,
        evaluated_at: str | None = None,
    ) -> OfflineSignalResult:
        normalized_symbol = self._validate_symbol(symbol)
        normalized_bars = tuple(bars)
        self._validate_bars(normalized_bars)

        closes = [bar.close for bar in normalized_bars]
        volumes = [bar.volume for bar in normalized_bars]
        fast_sma = _sma(closes, self.policy.fast_sma)
        slow_sma = _sma(closes, self.policy.slow_sma)
        rsi = _rsi(closes, self.policy.rsi_period)
        ema_fast_series = _ema_series(closes, self.policy.ema_fast)
        ema_slow_series = _ema_series(closes, self.policy.ema_slow)
        macd_series = [a - b for a, b in zip(ema_fast_series, ema_slow_series)]
        macd_signal_series = _ema_series(macd_series, self.policy.ema_signal)
        macd = macd_series[-1]
        macd_signal = macd_signal_series[-1]
        macd_histogram = macd - macd_signal
        latest_return = closes[-1] / closes[-2] - 1.0

        trend_component = _clip((fast_sma / slow_sma - 1.0) * 20.0)
        momentum_component = _clip((rsi - 50.0) / 25.0)
        macd_component = _clip(macd_histogram / max(abs(closes[-1]) * 0.01, 1e-12))
        stability_component = _clip(1.0 - abs(latest_return) / self.policy.max_abs_return, 0.0, 1.0)
        volume_gate = 1.0 if volumes[-1] >= self.policy.min_volume else 0.0

        raw_score = (
            0.45 * trend_component
            + 0.30 * momentum_component
            + 0.25 * macd_component
        )
        score = round(_clip(raw_score) * stability_component * volume_gate, 6)
        confidence = round(min(1.0, abs(score) * 0.75 + stability_component * 0.25), 6)

        if volume_gate == 0.0:
            action = SignalAction.HOLD
            reason = "HOLD: latest volume is below the offline policy minimum"
        elif abs(latest_return) > self.policy.max_abs_return:
            action = SignalAction.HOLD
            reason = "HOLD: abnormal one-bar return triggered the stability guard"
        elif score >= self.policy.buy_threshold:
            action = SignalAction.BUY
            reason = "BUY: trend, momentum, and MACD consensus exceeded the buy threshold"
        elif score <= self.policy.sell_threshold:
            action = SignalAction.SELL
            reason = "SELL: trend, momentum, and MACD consensus crossed the sell threshold"
        else:
            action = SignalAction.HOLD
            reason = "HOLD: composite score remained inside the neutral zone"

        timestamp = evaluated_at or datetime.now(timezone.utc).isoformat()
        _validate_iso_timestamp(timestamp, "evaluated_at")

        indicators = IndicatorSnapshot(
            close=round(closes[-1], 8),
            fast_sma=round(fast_sma, 8),
            slow_sma=round(slow_sma, 8),
            rsi=round(rsi, 8),
            macd=round(macd, 8),
            macd_signal=round(macd_signal, 8),
            macd_histogram=round(macd_histogram, 8),
            latest_return=round(latest_return, 8),
            volume=round(volumes[-1], 8),
        )
        components = SignalComponents(
            trend=round(trend_component, 8),
            momentum=round(momentum_component, 8),
            macd=round(macd_component, 8),
            stability=round(stability_component, 8),
            volume_gate=round(volume_gate, 8),
        )
        input_hash = _hash_json([asdict(bar) for bar in normalized_bars])
        policy_hash = _hash_json(asdict(self.policy))
        payload = {
            "version": VERSION,
            "engine": ENGINE_NAME,
            "symbol": normalized_symbol,
            "action": action.value,
            "score": score,
            "confidence": confidence,
            "reason": reason,
            "bars_used": len(normalized_bars),
            "evaluated_at": timestamp,
            "indicators": asdict(indicators),
            "components": asdict(components),
            "input_hash": input_hash,
            "policy_hash": policy_hash,
            "offline_only": True,
            "broker_blocked": True,
            "live_execution_blocked": True,
        }
        result_hash = _hash_json(payload)
        return OfflineSignalResult(
            version=VERSION,
            engine=ENGINE_NAME,
            symbol=normalized_symbol,
            action=action.value,
            score=score,
            confidence=confidence,
            reason=reason,
            bars_used=len(normalized_bars),
            evaluated_at=timestamp,
            indicators=indicators,
            components=components,
            input_hash=input_hash,
            policy_hash=policy_hash,
            result_hash=result_hash,
            offline_only=True,
            broker_blocked=True,
            live_execution_blocked=True,
        )

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str):
            raise TypeError("symbol must be a string")
        normalized = symbol.strip().upper()
        if not normalized or len(normalized) > 15:
            raise ValueError("symbol must contain 1 to 15 characters")
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_")
        if any(char not in allowed for char in normalized):
            raise ValueError("symbol contains unsupported characters")
        return normalized

    def _validate_bars(self, bars: Sequence[PriceBar]) -> None:
        required = max(
            self.policy.min_bars,
            self.policy.slow_sma,
            self.policy.rsi_period + 1,
            self.policy.ema_slow + self.policy.ema_signal,
        )
        if len(bars) < required:
            raise ValueError(f"at least {required} bars are required")
        previous_time: datetime | None = None
        for index, bar in enumerate(bars):
            if not isinstance(bar, PriceBar):
                raise TypeError(f"bar {index} must be PriceBar")
            current_time = _validate_iso_timestamp(bar.timestamp, f"bar {index} timestamp")
            if previous_time is not None and current_time <= previous_time:
                raise ValueError("bar timestamps must be strictly increasing")
            previous_time = current_time
            values = (bar.open, bar.high, bar.low, bar.close, bar.volume)
            if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
                raise ValueError(f"bar {index} contains non-finite numeric data")
            if min(bar.open, bar.high, bar.low, bar.close) <= 0:
                raise ValueError(f"bar {index} prices must be positive")
            if bar.volume < 0:
                raise ValueError(f"bar {index} volume cannot be negative")
            if bar.high < max(bar.open, bar.close, bar.low):
                raise ValueError(f"bar {index} high is inconsistent")
            if bar.low > min(bar.open, bar.close, bar.high):
                raise ValueError(f"bar {index} low is inconsistent")


def verify_result(result: OfflineSignalResult) -> bool:
    if not isinstance(result, OfflineSignalResult):
        return False
    if result.version != VERSION or result.engine != ENGINE_NAME:
        return False
    if result.action not in {item.value for item in SignalAction}:
        return False
    if not (-1.0 <= result.score <= 1.0 and 0.0 <= result.confidence <= 1.0):
        return False
    if not (result.offline_only and result.broker_blocked and result.live_execution_blocked):
        return False
    payload = asdict(result)
    supplied_hash = payload.pop("result_hash")
    return _hash_json(payload) == supplied_hash


def save_result(result: OfflineSignalResult, path: str | Path) -> None:
    if not verify_result(result):
        raise ValueError("cannot save an invalid signal result")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(result), indent=2, sort_keys=True), encoding="utf-8")


def load_result(path: str | Path) -> OfflineSignalResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    payload["indicators"] = IndicatorSnapshot(**payload["indicators"])
    payload["components"] = SignalComponents(**payload["components"])
    result = OfflineSignalResult(**payload)
    if not verify_result(result):
        raise ValueError("loaded signal result failed verification")
    return result


def broker_order(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Broker order creation is blocked in V25.0 offline mode")


def submit_order(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Order submission is blocked in V25.0 offline mode")


def authorize_live_execution(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("Live execution is blocked in V25.0 offline mode")


def _sma(values: Sequence[float], period: int) -> float:
    return sum(values[-period:]) / period


def _ema_series(values: Sequence[float], period: int) -> list[float]:
    if not values:
        raise ValueError("EMA values cannot be empty")
    alpha = 2.0 / (period + 1.0)
    output = [float(values[0])]
    for value in values[1:]:
        output.append(alpha * float(value) + (1.0 - alpha) * output[-1])
    return output


def _rsi(values: Sequence[float], period: int) -> float:
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-period:]
    gains = sum(max(change, 0.0) for change in recent) / period
    losses = sum(max(-change, 0.0) for change in recent) / period
    if losses == 0.0:
        return 100.0 if gains > 0.0 else 50.0
    relative_strength = gains / losses
    return 100.0 - 100.0 / (1.0 + relative_strength)


def _clip(value: float, minimum: float = -1.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _hash_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_iso_timestamp(value: str, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone information")
    return parsed
