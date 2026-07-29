from __future__ import annotations

"""
V26.0 Offline Data Feed Engine

Features:
- CSV loading
- multi-symbol datasets
- OHLCV validation
- duplicate and ordering checks
- missing-bar detection
- optional forward-fill repair
- timeframe aggregation
- deterministic dataset hashing
- JSON persistence and tamper detection

Safety boundary:
- no network access
- no broker/account APIs
- no live execution
"""

from dataclasses import dataclass, replace
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import csv
import json

VERSION = "26.0"
ZERO = Decimal("0")
CENT = Decimal("0.01")
QTY_STEP = Decimal("0.000001")


class DataFeedError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise DataFeedError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise DataFeedError("decimal value must be finite")
    return result


def _money(value: Any) -> Decimal:
    return _d(value).quantize(CENT, rounding=ROUND_HALF_UP)


def _qty(value: Any) -> Decimal:
    return _d(value).quantize(QTY_STEP, rounding=ROUND_HALF_UP)


def _symbol(value: str) -> str:
    result = value.strip().upper()
    if not result or len(result) > 15 or not all(ch.isalnum() or ch in ".-" for ch in result):
        raise DataFeedError("invalid symbol")
    return result


def _timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataFeedError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise DataFeedError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    timestamp: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class DataSet:
    version: str
    timeframe_minutes: int
    bars: tuple[MarketBar, ...]
    symbols: tuple[str, ...]
    dataset_hash: str


def _bar_payload(bar: MarketBar) -> dict[str, str]:
    return {
        "symbol": bar.symbol,
        "timestamp": bar.timestamp,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
        "volume": str(bar.volume),
    }


def _dataset_payload(dataset: DataSet, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": dataset.version,
        "timeframe_minutes": dataset.timeframe_minutes,
        "bars": [_bar_payload(bar) for bar in dataset.bars],
        "symbols": list(dataset.symbols),
    }
    if include_hash:
        payload["dataset_hash"] = dataset.dataset_hash
    return payload


def _normalize_bar(bar: MarketBar) -> MarketBar:
    symbol = _symbol(bar.symbol)
    timestamp = _timestamp(bar.timestamp)
    o = _money(bar.open)
    h = _money(bar.high)
    l = _money(bar.low)
    c = _money(bar.close)
    v = _qty(bar.volume)

    if min(o, h, l, c) <= ZERO:
        raise DataFeedError("OHLC prices must be positive")
    if v < ZERO:
        raise DataFeedError("volume cannot be negative")
    if h < max(o, l, c):
        raise DataFeedError("high is below another OHLC value")
    if l > min(o, h, c):
        raise DataFeedError("low is above another OHLC value")

    return MarketBar(symbol, timestamp, o, h, l, c, v)


def create_dataset(
    bars: Iterable[MarketBar],
    timeframe_minutes: int,
) -> DataSet:
    if timeframe_minutes <= 0:
        raise DataFeedError("timeframe_minutes must be positive")

    normalized = tuple(
        sorted(
            (_normalize_bar(bar) for bar in bars),
            key=lambda bar: (bar.symbol, bar.timestamp),
        )
    )
    if not normalized:
        raise DataFeedError("dataset cannot be empty")

    keys = [(bar.symbol, bar.timestamp) for bar in normalized]
    if len(keys) != len(set(keys)):
        raise DataFeedError("duplicate symbol/timestamp bars detected")

    by_symbol: dict[str, list[MarketBar]] = {}
    for bar in normalized:
        by_symbol.setdefault(bar.symbol, []).append(bar)

    for symbol, items in by_symbol.items():
        times = [bar.timestamp for bar in items]
        if times != sorted(times):
            raise DataFeedError(f"timestamps are not increasing for {symbol}")

    dataset = DataSet(
        version=VERSION,
        timeframe_minutes=int(timeframe_minutes),
        bars=normalized,
        symbols=tuple(sorted(by_symbol)),
        dataset_hash="",
    )
    return replace(dataset, dataset_hash=_hash(_dataset_payload(dataset)))


def load_csv(path: str | Path, timeframe_minutes: int) -> DataSet:
    source = Path(path)
    if not source.exists():
        raise DataFeedError("CSV file not found")

    bars: list[MarketBar] = []
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"symbol", "timestamp", "open", "high", "low", "close", "volume"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise DataFeedError("CSV is missing required columns")

        for row in reader:
            bars.append(MarketBar(
                symbol=row["symbol"],
                timestamp=row["timestamp"],
                open=_d(row["open"]),
                high=_d(row["high"]),
                low=_d(row["low"]),
                close=_d(row["close"]),
                volume=_d(row["volume"]),
            ))

    return create_dataset(bars, timeframe_minutes)


def bars_for_symbol(dataset: DataSet, symbol: str) -> tuple[MarketBar, ...]:
    verify_dataset(dataset)
    normalized = _symbol(symbol)
    return tuple(bar for bar in dataset.bars if bar.symbol == normalized)


def detect_missing_bars(dataset: DataSet) -> dict[str, tuple[str, ...]]:
    verify_dataset(dataset)
    step = timedelta(minutes=dataset.timeframe_minutes)
    missing: dict[str, tuple[str, ...]] = {}

    for symbol in dataset.symbols:
        items = bars_for_symbol(dataset, symbol)
        gaps: list[str] = []
        for left, right in zip(items, items[1:]):
            current = datetime.fromisoformat(left.timestamp)
            target = datetime.fromisoformat(right.timestamp)
            cursor = current + step
            while cursor < target:
                gaps.append(cursor.astimezone(timezone.utc).isoformat())
                cursor += step
        missing[symbol] = tuple(gaps)

    return missing


def forward_fill_missing(dataset: DataSet) -> DataSet:
    verify_dataset(dataset)
    step = timedelta(minutes=dataset.timeframe_minutes)
    repaired: list[MarketBar] = []

    for symbol in dataset.symbols:
        items = list(bars_for_symbol(dataset, symbol))
        for index, bar in enumerate(items):
            repaired.append(bar)
            if index == len(items) - 1:
                continue

            next_time = datetime.fromisoformat(items[index + 1].timestamp)
            cursor = datetime.fromisoformat(bar.timestamp) + step
            while cursor < next_time:
                repaired.append(MarketBar(
                    symbol=symbol,
                    timestamp=cursor.astimezone(timezone.utc).isoformat(),
                    open=bar.close,
                    high=bar.close,
                    low=bar.close,
                    close=bar.close,
                    volume=ZERO,
                ))
                cursor += step

    return create_dataset(repaired, dataset.timeframe_minutes)


def resample(dataset: DataSet, target_minutes: int) -> DataSet:
    verify_dataset(dataset)
    if target_minutes <= dataset.timeframe_minutes:
        raise DataFeedError("target timeframe must be larger than source timeframe")
    if target_minutes % dataset.timeframe_minutes != 0:
        raise DataFeedError("target timeframe must be a whole multiple of source timeframe")

    ratio = target_minutes // dataset.timeframe_minutes
    output: list[MarketBar] = []

    for symbol in dataset.symbols:
        items = list(bars_for_symbol(dataset, symbol))
        for start in range(0, len(items), ratio):
            chunk = items[start:start + ratio]
            if len(chunk) != ratio:
                continue
            output.append(MarketBar(
                symbol=symbol,
                timestamp=chunk[0].timestamp,
                open=chunk[0].open,
                high=max(bar.high for bar in chunk),
                low=min(bar.low for bar in chunk),
                close=chunk[-1].close,
                volume=sum((bar.volume for bar in chunk), ZERO),
            ))

    if not output:
        raise DataFeedError("not enough bars to resample")
    return create_dataset(output, target_minutes)


def verify_dataset(dataset: DataSet) -> bool:
    if dataset.version != VERSION:
        raise DataFeedError("unsupported dataset version")
    if dataset.timeframe_minutes <= 0:
        raise DataFeedError("invalid timeframe")
    if not dataset.bars:
        raise DataFeedError("dataset cannot be empty")
    if tuple(sorted(set(bar.symbol for bar in dataset.bars))) != dataset.symbols:
        raise DataFeedError("symbol index mismatch")

    normalized = tuple(
        sorted(
            (_normalize_bar(bar) for bar in dataset.bars),
            key=lambda bar: (bar.symbol, bar.timestamp),
        )
    )
    if normalized != dataset.bars:
        raise DataFeedError("bars are not normalized and sorted")

    keys = [(bar.symbol, bar.timestamp) for bar in dataset.bars]
    if len(keys) != len(set(keys)):
        raise DataFeedError("duplicate bars detected")

    clean = replace(dataset, dataset_hash="")
    if dataset.dataset_hash != _hash(_dataset_payload(clean)):
        raise DataFeedError("dataset hash mismatch")
    return True


def save_dataset(dataset: DataSet, path: str | Path) -> Path:
    verify_dataset(dataset)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_dataset_payload(dataset, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_dataset(path: str | Path) -> DataSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    bars = tuple(MarketBar(
        symbol=item["symbol"],
        timestamp=item["timestamp"],
        open=_d(item["open"]),
        high=_d(item["high"]),
        low=_d(item["low"]),
        close=_d(item["close"]),
        volume=_d(item["volume"]),
    ) for item in payload["bars"])

    dataset = DataSet(
        version=payload["version"],
        timeframe_minutes=int(payload["timeframe_minutes"]),
        bars=bars,
        symbols=tuple(payload["symbols"]),
        dataset_hash=payload["dataset_hash"],
    )
    verify_dataset(dataset)
    return dataset


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
