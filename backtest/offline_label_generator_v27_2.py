from __future__ import annotations

"""
V27.2 Offline Label Generator

Creates deterministic supervised-learning labels from future price movement.

Features:
- BUY / HOLD / SELL labels
- optional STRONG_BUY / STRONG_SELL labels
- future-return labeling
- take-profit / stop-loss barrier evaluation
- maximum holding horizon
- tie-breaking policy
- leakage-safe feature/label alignment
- class-distribution reporting
- imbalance ratio calculation
- row and label-set SHA-256 hashes
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
from pathlib import Path
from typing import Any, Iterable
import json

VERSION = "27.2"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class LabelError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise LabelError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise LabelError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PricePoint:
    timestamp: str
    close: Decimal
    high: Decimal
    low: Decimal


@dataclass(frozen=True)
class LabelPolicy:
    horizon_bars: int = 5
    buy_threshold_pct: Decimal = Decimal("2.0")
    sell_threshold_pct: Decimal = Decimal("-2.0")
    strong_buy_threshold_pct: Decimal = Decimal("5.0")
    strong_sell_threshold_pct: Decimal = Decimal("-5.0")
    use_strong_labels: bool = True
    take_profit_pct: Decimal = Decimal("3.0")
    stop_loss_pct: Decimal = Decimal("2.0")
    barrier_mode: bool = True
    tie_breaker: str = "STOP_FIRST"
    drop_incomplete_horizon: bool = True

    def __post_init__(self) -> None:
        if self.horizon_bars <= 0:
            raise LabelError("horizon_bars must be positive")
        if _d(self.sell_threshold_pct) >= _d(self.buy_threshold_pct):
            raise LabelError("sell threshold must be below buy threshold")
        if _d(self.strong_sell_threshold_pct) >= _d(self.sell_threshold_pct):
            raise LabelError("strong sell threshold must be below sell threshold")
        if _d(self.strong_buy_threshold_pct) <= _d(self.buy_threshold_pct):
            raise LabelError("strong buy threshold must exceed buy threshold")
        if _d(self.take_profit_pct) <= ZERO or _d(self.stop_loss_pct) <= ZERO:
            raise LabelError("barrier percentages must be positive")
        if self.tie_breaker.upper() not in {"STOP_FIRST", "TARGET_FIRST", "HOLD"}:
            raise LabelError("unsupported tie breaker")


@dataclass(frozen=True)
class LabelRow:
    timestamp: str
    entry_price: Decimal
    future_close: Decimal
    future_return_pct: Decimal
    max_favorable_excursion_pct: Decimal
    max_adverse_excursion_pct: Decimal
    label: str
    label_code: int
    horizon_complete: bool
    row_hash: str


@dataclass(frozen=True)
class ClassStat:
    label: str
    count: int
    percentage: Decimal


@dataclass(frozen=True)
class LabelSet:
    version: str
    rows: tuple[LabelRow, ...]
    class_distribution: tuple[ClassStat, ...]
    imbalance_ratio: Decimal
    input_hash: str
    label_hash: str


LABEL_CODES = {
    "STRONG_SELL": -2,
    "SELL": -1,
    "HOLD": 0,
    "BUY": 1,
    "STRONG_BUY": 2,
}


def _point_payload(point: PricePoint) -> dict[str, str]:
    return {
        "timestamp": point.timestamp,
        "close": str(point.close),
        "high": str(point.high),
        "low": str(point.low),
    }


def _row_payload(row: LabelRow, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "timestamp": row.timestamp,
        "entry_price": str(row.entry_price),
        "future_close": str(row.future_close),
        "future_return_pct": str(row.future_return_pct),
        "max_favorable_excursion_pct": str(row.max_favorable_excursion_pct),
        "max_adverse_excursion_pct": str(row.max_adverse_excursion_pct),
        "label": row.label,
        "label_code": row.label_code,
        "horizon_complete": row.horizon_complete,
    }
    if include_hash:
        payload["row_hash"] = row.row_hash
    return payload


def _stat_payload(stat: ClassStat) -> dict[str, Any]:
    return {
        "label": stat.label,
        "count": stat.count,
        "percentage": str(stat.percentage),
    }


def _set_payload(label_set: LabelSet, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": label_set.version,
        "rows": [_row_payload(row, include_hash=True) for row in label_set.rows],
        "class_distribution": [_stat_payload(stat) for stat in label_set.class_distribution],
        "imbalance_ratio": str(label_set.imbalance_ratio),
        "input_hash": label_set.input_hash,
    }
    if include_hash:
        payload["label_hash"] = label_set.label_hash
    return payload


def _normalize_points(items: Iterable[PricePoint]) -> tuple[PricePoint, ...]:
    points = []
    for item in items:
        if not item.timestamp:
            raise LabelError("timestamp is required")
        close = _q(item.close)
        high = _q(item.high)
        low = _q(item.low)
        if min(close, high, low) <= ZERO:
            raise LabelError("prices must be positive")
        if high < close or low > close or high < low:
            raise LabelError("invalid price range")
        points.append(PricePoint(item.timestamp, close, high, low))

    if len(points) < 2:
        raise LabelError("at least two price points are required")

    timestamps = [point.timestamp for point in points]
    if timestamps != sorted(timestamps):
        raise LabelError("timestamps must be increasing")
    if len(timestamps) != len(set(timestamps)):
        raise LabelError("duplicate timestamps detected")
    return tuple(points)


def _return_pct(entry: Decimal, exit_price: Decimal) -> Decimal:
    return _q((exit_price - entry) / entry * Decimal("100"))


def _barrier_label(
    entry: Decimal,
    future: tuple[PricePoint, ...],
    policy: LabelPolicy,
) -> str | None:
    target = entry * (Decimal("1") + _d(policy.take_profit_pct) / Decimal("100"))
    stop = entry * (Decimal("1") - _d(policy.stop_loss_pct) / Decimal("100"))

    for point in future:
        target_hit = point.high >= target
        stop_hit = point.low <= stop

        if target_hit and stop_hit:
            tie = policy.tie_breaker.upper()
            if tie == "TARGET_FIRST":
                return "BUY"
            if tie == "STOP_FIRST":
                return "SELL"
            return "HOLD"
        if target_hit:
            return "BUY"
        if stop_hit:
            return "SELL"
    return None


def _return_label(return_pct: Decimal, policy: LabelPolicy) -> str:
    if policy.use_strong_labels:
        if return_pct >= _d(policy.strong_buy_threshold_pct):
            return "STRONG_BUY"
        if return_pct <= _d(policy.strong_sell_threshold_pct):
            return "STRONG_SELL"

    if return_pct >= _d(policy.buy_threshold_pct):
        return "BUY"
    if return_pct <= _d(policy.sell_threshold_pct):
        return "SELL"
    return "HOLD"


def generate_labels(
    price_points: Iterable[PricePoint],
    policy: LabelPolicy | None = None,
) -> LabelSet:
    selected = policy or LabelPolicy()
    points = _normalize_points(price_points)
    rows: list[LabelRow] = []

    for index, point in enumerate(points):
        end_index = index + selected.horizon_bars
        complete = end_index < len(points)

        if not complete and selected.drop_incomplete_horizon:
            continue

        effective_end = min(end_index, len(points) - 1)
        if effective_end <= index:
            continue

        future_window = points[index + 1:effective_end + 1]
        future_close = points[effective_end].close
        future_return = _return_pct(point.close, future_close)

        max_high = max(item.high for item in future_window)
        min_low = min(item.low for item in future_window)
        mfe = _q((max_high - point.close) / point.close * Decimal("100"))
        mae = _q((min_low - point.close) / point.close * Decimal("100"))

        label = None
        if selected.barrier_mode:
            label = _barrier_label(point.close, future_window, selected)

        if label is None:
            label = _return_label(future_return, selected)

        if selected.use_strong_labels and label == "BUY":
            if future_return >= _d(selected.strong_buy_threshold_pct):
                label = "STRONG_BUY"
        if selected.use_strong_labels and label == "SELL":
            if future_return <= _d(selected.strong_sell_threshold_pct):
                label = "STRONG_SELL"

        row = LabelRow(
            timestamp=point.timestamp,
            entry_price=point.close,
            future_close=future_close,
            future_return_pct=future_return,
            max_favorable_excursion_pct=mfe,
            max_adverse_excursion_pct=mae,
            label=label,
            label_code=LABEL_CODES[label],
            horizon_complete=complete,
            row_hash="",
        )
        rows.append(replace(row, row_hash=_hash(_row_payload(row))))

    if not rows:
        raise LabelError("no label rows were produced")

    counts = {label: 0 for label in LABEL_CODES}
    for row in rows:
        counts[row.label] += 1

    distribution = tuple(
        ClassStat(
            label=label,
            count=counts[label],
            percentage=_q(Decimal(counts[label]) / Decimal(len(rows)) * Decimal("100")),
        )
        for label in LABEL_CODES
        if counts[label] > 0
    )

    nonzero_counts = [stat.count for stat in distribution if stat.count > 0]
    imbalance = (
        _q(Decimal(max(nonzero_counts)) / Decimal(min(nonzero_counts)))
        if nonzero_counts else ZERO
    )

    input_hash = _hash({
        "points": [_point_payload(point) for point in points],
        "policy": {
            key: str(value)
            for key, value in selected.__dict__.items()
        },
    })

    result = LabelSet(
        version=VERSION,
        rows=tuple(rows),
        class_distribution=distribution,
        imbalance_ratio=imbalance,
        input_hash=input_hash,
        label_hash="",
    )
    return replace(result, label_hash=_hash(_set_payload(result)))


def align_features_and_labels(
    feature_timestamps: Iterable[str],
    label_set: LabelSet,
) -> tuple[tuple[str, int], ...]:
    verify_label_set(label_set)
    label_map = {row.timestamp: row.label_code for row in label_set.rows}
    aligned = []
    seen = set()

    for timestamp in feature_timestamps:
        if timestamp in seen:
            raise LabelError("duplicate feature timestamp detected")
        seen.add(timestamp)
        if timestamp in label_map:
            aligned.append((timestamp, label_map[timestamp]))

    if not aligned:
        raise LabelError("no feature timestamps aligned with labels")
    return tuple(aligned)


def verify_row(row: LabelRow) -> bool:
    if row.label not in LABEL_CODES:
        raise LabelError("invalid label")
    if row.label_code != LABEL_CODES[row.label]:
        raise LabelError("label code mismatch")
    if row.entry_price <= ZERO or row.future_close <= ZERO:
        raise LabelError("invalid prices")
    clean = replace(row, row_hash="")
    if row.row_hash != _hash(_row_payload(clean)):
        raise LabelError("label row hash mismatch")
    return True


def verify_label_set(label_set: LabelSet) -> bool:
    if label_set.version != VERSION:
        raise LabelError("unsupported label-set version")
    if not label_set.rows:
        raise LabelError("label set cannot be empty")

    timestamps = [row.timestamp for row in label_set.rows]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise LabelError("label rows must have unique increasing timestamps")

    for row in label_set.rows:
        verify_row(row)

    total = sum(stat.count for stat in label_set.class_distribution)
    if total != len(label_set.rows):
        raise LabelError("class-distribution count mismatch")

    clean = replace(label_set, label_hash="")
    if label_set.label_hash != _hash(_set_payload(clean)):
        raise LabelError("label-set hash mismatch")
    return True


def save_label_set(label_set: LabelSet, path: str | Path) -> Path:
    verify_label_set(label_set)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_set_payload(label_set, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_label_set(path: str | Path) -> LabelSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = tuple(
        LabelRow(
            timestamp=item["timestamp"],
            entry_price=_d(item["entry_price"]),
            future_close=_d(item["future_close"]),
            future_return_pct=_d(item["future_return_pct"]),
            max_favorable_excursion_pct=_d(item["max_favorable_excursion_pct"]),
            max_adverse_excursion_pct=_d(item["max_adverse_excursion_pct"]),
            label=item["label"],
            label_code=int(item["label_code"]),
            horizon_complete=bool(item["horizon_complete"]),
            row_hash=item["row_hash"],
        )
        for item in payload["rows"]
    )
    distribution = tuple(
        ClassStat(
            label=item["label"],
            count=int(item["count"]),
            percentage=_d(item["percentage"]),
        )
        for item in payload["class_distribution"]
    )
    result = LabelSet(
        version=payload["version"],
        rows=rows,
        class_distribution=distribution,
        imbalance_ratio=_d(payload["imbalance_ratio"]),
        input_hash=payload["input_hash"],
        label_hash=payload["label_hash"],
    )
    verify_label_set(result)
    return result


MARKET_DATA_API_CALLED = False
ACCOUNT_API_CALLED = False
NETWORK_ACCESSED = False
BROKER_API_CALLED = False
BROKER_ORDER_CREATED = False
ORDER_SUBMITTED = False
LIVE_EXECUTION_AUTHORIZED = False
FUNDS_RESERVED = False
HOLDINGS_RESERVED = False
