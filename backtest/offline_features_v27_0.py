from __future__ import annotations

"""
V27.0 Offline Feature Engineering Engine

Transforms deterministic OHLCV input into AI-ready technical features.

Features:
- SMA / EMA
- RSI
- MACD and signal line
- ATR
- Bollinger Band width and z-score
- ROC and momentum
- historical volatility
- OBV and relative volume
- candle body, wick ratios, gap, range
- breakout and trend-strength features
- missing warmup values represented as None
- canonical SHA-256 feature-set hashing
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no account/broker APIs
- no order creation/submission
- no live execution
"""

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from math import sqrt
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable
import json

VERSION = "27.0"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class FeatureError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise FeatureError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise FeatureError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class FeaturePolicy:
    sma_fast: int = 5
    sma_slow: int = 20
    ema_fast: int = 12
    ema_slow: int = 26
    rsi_period: int = 14
    macd_signal_period: int = 9
    atr_period: int = 14
    bollinger_period: int = 20
    bollinger_stddev: Decimal = Decimal("2")
    roc_period: int = 10
    volatility_period: int = 20
    volume_period: int = 20
    breakout_period: int = 20

    def __post_init__(self) -> None:
        integer_fields = (
            "sma_fast", "sma_slow", "ema_fast", "ema_slow", "rsi_period",
            "macd_signal_period", "atr_period", "bollinger_period",
            "roc_period", "volatility_period", "volume_period", "breakout_period",
        )
        for name in integer_fields:
            if int(getattr(self, name)) <= 0:
                raise FeatureError(f"{name} must be positive")
        if self.sma_fast >= self.sma_slow:
            raise FeatureError("sma_fast must be below sma_slow")
        if self.ema_fast >= self.ema_slow:
            raise FeatureError("ema_fast must be below ema_slow")
        if _d(self.bollinger_stddev) <= ZERO:
            raise FeatureError("bollinger_stddev must be positive")


@dataclass(frozen=True)
class FeatureRow:
    timestamp: str
    close: Decimal
    features: tuple[tuple[str, Decimal | None], ...]
    row_hash: str


@dataclass(frozen=True)
class FeatureSet:
    version: str
    feature_names: tuple[str, ...]
    rows: tuple[FeatureRow, ...]
    input_hash: str
    feature_hash: str


def _bar_payload(bar: PriceBar) -> dict[str, str]:
    return {
        "timestamp": bar.timestamp,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }


def _row_payload(row: FeatureRow, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "timestamp": row.timestamp,
        "close": str(row.close),
        "features": {
            key: None if value is None else str(value)
            for key, value in row.features
        },
    }
    if include_hash:
        payload["row_hash"] = row.row_hash
    return payload


def _set_payload(feature_set: FeatureSet, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": feature_set.version,
        "feature_names": list(feature_set.feature_names),
        "rows": [_row_payload(row, include_hash=True) for row in feature_set.rows],
        "input_hash": feature_set.input_hash,
    }
    if include_hash:
        payload["feature_hash"] = feature_set.feature_hash
    return payload


def _normalize_bars(items: Iterable[PriceBar]) -> tuple[PriceBar, ...]:
    bars = []
    for item in items:
        if not item.timestamp:
            raise FeatureError("timestamp is required")
        o, h, l, c, v = map(_d, (item.open, item.high, item.low, item.close, item.volume))
        if min(o, h, l, c) <= ZERO:
            raise FeatureError("OHLC values must be positive")
        if v < ZERO:
            raise FeatureError("volume cannot be negative")
        if h < max(o, l, c) or l > min(o, h, c):
            raise FeatureError("invalid OHLC range")
        bars.append(PriceBar(
            timestamp=item.timestamp,
            open=_q(o),
            high=_q(h),
            low=_q(l),
            close=_q(c),
            volume=_q(v),
        ))
    if len(bars) < 2:
        raise FeatureError("at least two bars are required")
    timestamps = [bar.timestamp for bar in bars]
    if timestamps != sorted(timestamps):
        raise FeatureError("timestamps must be increasing")
    if len(timestamps) != len(set(timestamps)):
        raise FeatureError("duplicate timestamps detected")
    return tuple(bars)


def _sma(values: list[Decimal], period: int, index: int) -> Decimal | None:
    if index + 1 < period:
        return None
    window = values[index - period + 1:index + 1]
    return _q(sum(window, ZERO) / Decimal(period))


def _ema_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    result: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period], ZERO) / Decimal(period)
    result[period - 1] = _q(seed)
    alpha = Decimal("2") / Decimal(period + 1)
    current = seed
    for index in range(period, len(values)):
        current = values[index] * alpha + current * (Decimal("1") - alpha)
        result[index] = _q(current)
    return result


def _rsi(values: list[Decimal], period: int, index: int) -> Decimal | None:
    if index < period:
        return None
    gains = []
    losses = []
    for pos in range(index - period + 1, index + 1):
        change = values[pos] - values[pos - 1]
        gains.append(max(change, ZERO))
        losses.append(max(-change, ZERO))
    avg_gain = sum(gains, ZERO) / Decimal(period)
    avg_loss = sum(losses, ZERO) / Decimal(period)
    if avg_loss == ZERO:
        return Decimal("100.0000") if avg_gain > ZERO else Decimal("50.0000")
    rs = avg_gain / avg_loss
    return _q(Decimal("100") - Decimal("100") / (Decimal("1") + rs))


def _true_ranges(bars: tuple[PriceBar, ...]) -> list[Decimal]:
    output = []
    for index, bar in enumerate(bars):
        if index == 0:
            tr = bar.high - bar.low
        else:
            previous_close = bars[index - 1].close
            tr = max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            )
        output.append(_q(tr))
    return output


def _atr(tr_values: list[Decimal], period: int, index: int) -> Decimal | None:
    if index + 1 < period:
        return None
    return _q(sum(tr_values[index - period + 1:index + 1], ZERO) / Decimal(period))


def _stddev(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return _d(pstdev([float(value) for value in values]))


def _obv_series(bars: tuple[PriceBar, ...]) -> list[Decimal]:
    output = [ZERO]
    current = ZERO
    for index in range(1, len(bars)):
        if bars[index].close > bars[index - 1].close:
            current += bars[index].volume
        elif bars[index].close < bars[index - 1].close:
            current -= bars[index].volume
        output.append(_q(current))
    return output


def build_features(
    bars: Iterable[PriceBar],
    policy: FeaturePolicy | None = None,
) -> FeatureSet:
    selected = policy or FeaturePolicy()
    data = _normalize_bars(bars)
    closes = [bar.close for bar in data]
    volumes = [bar.volume for bar in data]
    tr_values = _true_ranges(data)
    ema_fast = _ema_series(closes, selected.ema_fast)
    ema_slow = _ema_series(closes, selected.ema_slow)

    macd_values: list[Decimal | None] = []
    for fast, slow in zip(ema_fast, ema_slow):
        macd_values.append(None if fast is None or slow is None else _q(fast - slow))

    macd_signal: list[Decimal | None] = [None] * len(data)
    valid_macd = [(i, value) for i, value in enumerate(macd_values) if value is not None]
    if len(valid_macd) >= selected.macd_signal_period:
        seed_values = [value for _, value in valid_macd[:selected.macd_signal_period]]
        current = sum(seed_values, ZERO) / Decimal(selected.macd_signal_period)
        seed_index = valid_macd[selected.macd_signal_period - 1][0]
        macd_signal[seed_index] = _q(current)
        alpha = Decimal("2") / Decimal(selected.macd_signal_period + 1)
        for index, value in valid_macd[selected.macd_signal_period:]:
            current = value * alpha + current * (Decimal("1") - alpha)
            macd_signal[index] = _q(current)

    obv = _obv_series(data)

    feature_names = (
        "sma_fast", "sma_slow", "ema_fast", "ema_slow",
        "rsi", "macd", "macd_signal", "macd_histogram",
        "atr", "bollinger_width", "bollinger_zscore",
        "roc", "momentum", "historical_volatility",
        "obv", "relative_volume",
        "candle_body_pct", "upper_wick_pct", "lower_wick_pct",
        "gap_pct", "range_pct", "breakout_up", "breakout_down",
        "trend_strength",
    )

    rows = []
    for index, bar in enumerate(data):
        sma_fast = _sma(closes, selected.sma_fast, index)
        sma_slow = _sma(closes, selected.sma_slow, index)
        rsi = _rsi(closes, selected.rsi_period, index)
        atr = _atr(tr_values, selected.atr_period, index)

        boll_width = boll_zscore = None
        if index + 1 >= selected.bollinger_period:
            window = closes[index - selected.bollinger_period + 1:index + 1]
            middle = sum(window, ZERO) / Decimal(selected.bollinger_period)
            std = _stddev(window)
            upper = middle + std * _d(selected.bollinger_stddev)
            lower = middle - std * _d(selected.bollinger_stddev)
            boll_width = _q((upper - lower) / middle) if middle != ZERO else None
            boll_zscore = _q((bar.close - middle) / std) if std != ZERO else ZERO

        roc = momentum = None
        if index >= selected.roc_period:
            base = closes[index - selected.roc_period]
            roc = _q((bar.close - base) / base * Decimal("100"))
            momentum = _q(bar.close - base)

        historical_volatility = None
        if index >= selected.volatility_period:
            returns = []
            start = index - selected.volatility_period + 1
            for pos in range(start, index + 1):
                previous = closes[pos - 1]
                returns.append(float((closes[pos] - previous) / previous))
            historical_volatility = _q(_stddev([_d(x) for x in returns]) * _d(sqrt(252)) * Decimal("100"))

        relative_volume = None
        if index + 1 >= selected.volume_period:
            volume_mean = sum(volumes[index - selected.volume_period + 1:index + 1], ZERO) / Decimal(selected.volume_period)
            relative_volume = _q(bar.volume / volume_mean) if volume_mean != ZERO else ZERO

        candle_range = bar.high - bar.low
        body = abs(bar.close - bar.open)
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low
        candle_body_pct = _q(body / candle_range) if candle_range != ZERO else ZERO
        upper_wick_pct = _q(upper_wick / candle_range) if candle_range != ZERO else ZERO
        lower_wick_pct = _q(lower_wick / candle_range) if candle_range != ZERO else ZERO
        gap_pct = None if index == 0 else _q((bar.open - data[index - 1].close) / data[index - 1].close * Decimal("100"))
        range_pct = _q(candle_range / bar.close * Decimal("100"))

        breakout_up = breakout_down = None
        if index >= selected.breakout_period:
            prior = data[index - selected.breakout_period:index]
            breakout_up = Decimal("1.0000") if bar.close > max(item.high for item in prior) else ZERO
            breakout_down = Decimal("1.0000") if bar.close < min(item.low for item in prior) else ZERO

        trend_strength = None
        if ema_fast[index] is not None and ema_slow[index] is not None and atr is not None and atr != ZERO:
            trend_strength = _q((ema_fast[index] - ema_slow[index]) / atr)

        macd_hist = None
        if macd_values[index] is not None and macd_signal[index] is not None:
            macd_hist = _q(macd_values[index] - macd_signal[index])

        values: dict[str, Decimal | None] = {
            "sma_fast": sma_fast,
            "sma_slow": sma_slow,
            "ema_fast": ema_fast[index],
            "ema_slow": ema_slow[index],
            "rsi": rsi,
            "macd": macd_values[index],
            "macd_signal": macd_signal[index],
            "macd_histogram": macd_hist,
            "atr": atr,
            "bollinger_width": boll_width,
            "bollinger_zscore": boll_zscore,
            "roc": roc,
            "momentum": momentum,
            "historical_volatility": historical_volatility,
            "obv": obv[index],
            "relative_volume": relative_volume,
            "candle_body_pct": candle_body_pct,
            "upper_wick_pct": upper_wick_pct,
            "lower_wick_pct": lower_wick_pct,
            "gap_pct": gap_pct,
            "range_pct": range_pct,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
            "trend_strength": trend_strength,
        }
        feature_tuple = tuple((name, values[name]) for name in feature_names)
        row = FeatureRow(
            timestamp=bar.timestamp,
            close=bar.close,
            features=feature_tuple,
            row_hash="",
        )
        rows.append(replace(row, row_hash=_hash(_row_payload(row))))

    input_hash = _hash({
        "bars": [_bar_payload(bar) for bar in data],
        "policy": {
            key: str(value)
            for key, value in selected.__dict__.items()
        },
    })
    result = FeatureSet(
        version=VERSION,
        feature_names=feature_names,
        rows=tuple(rows),
        input_hash=input_hash,
        feature_hash="",
    )
    return replace(result, feature_hash=_hash(_set_payload(result)))


def verify_row(row: FeatureRow, feature_names: tuple[str, ...]) -> bool:
    if tuple(name for name, _ in row.features) != feature_names:
        raise FeatureError("feature row schema mismatch")
    if row.close <= ZERO:
        raise FeatureError("row close must be positive")
    clean = replace(row, row_hash="")
    if row.row_hash != _hash(_row_payload(clean)):
        raise FeatureError("row hash mismatch")
    return True


def verify_feature_set(feature_set: FeatureSet) -> bool:
    if feature_set.version != VERSION:
        raise FeatureError("unsupported feature-set version")
    if not feature_set.feature_names or not feature_set.rows:
        raise FeatureError("feature set cannot be empty")
    timestamps = [row.timestamp for row in feature_set.rows]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise FeatureError("feature rows must have unique increasing timestamps")
    for row in feature_set.rows:
        verify_row(row, feature_set.feature_names)
    clean = replace(feature_set, feature_hash="")
    if feature_set.feature_hash != _hash(_set_payload(clean)):
        raise FeatureError("feature-set hash mismatch")
    return True


def save_feature_set(feature_set: FeatureSet, path: str | Path) -> Path:
    verify_feature_set(feature_set)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_set_payload(feature_set, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_feature_set(path: str | Path) -> FeatureSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    feature_names = tuple(payload["feature_names"])
    for item in payload["rows"]:
        features = tuple(
            (name, None if item["features"][name] is None else _d(item["features"][name]))
            for name in feature_names
        )
        rows.append(FeatureRow(
            timestamp=item["timestamp"],
            close=_d(item["close"]),
            features=features,
            row_hash=item["row_hash"],
        ))
    feature_set = FeatureSet(
        version=payload["version"],
        feature_names=feature_names,
        rows=tuple(rows),
        input_hash=payload["input_hash"],
        feature_hash=payload["feature_hash"],
    )
    verify_feature_set(feature_set)
    return feature_set


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
