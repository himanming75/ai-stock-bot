from __future__ import annotations

"""
V27.3 Offline Train/Validation Split Engine

Features:
- deterministic random split
- stratified split
- time-series split
- optional shuffle with fixed seed
- class-distribution checks
- leakage prevention
- split hashing
- JSON persistence
- tamper detection

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
import random

VERSION = "27.3"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class SplitError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise SplitError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise SplitError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DatasetRow:
    row_id: str
    timestamp: str
    features: tuple[Decimal, ...]
    label: int


@dataclass(frozen=True)
class SplitPolicy:
    validation_ratio: Decimal = Decimal("0.20")
    mode: str = "STRATIFIED"
    shuffle: bool = True
    random_seed: int = 42
    purge_size: int = 0

    def __post_init__(self) -> None:
        ratio = _d(self.validation_ratio)
        if ratio <= ZERO or ratio >= Decimal("1"):
            raise SplitError("validation_ratio must be between 0 and 1")
        if self.mode.upper() not in {"RANDOM", "STRATIFIED", "TIME_SERIES"}:
            raise SplitError("unsupported split mode")
        if self.purge_size < 0:
            raise SplitError("purge_size cannot be negative")
        if self.mode.upper() == "TIME_SERIES" and self.shuffle:
            raise SplitError("time-series split cannot shuffle")


@dataclass(frozen=True)
class ClassCount:
    label: int
    train_count: int
    validation_count: int


@dataclass(frozen=True)
class SplitResult:
    version: str
    mode: str
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    purged_ids: tuple[str, ...]
    class_counts: tuple[ClassCount, ...]
    train_ratio: Decimal
    validation_ratio: Decimal
    input_hash: str
    split_hash: str


def _row_payload(row: DatasetRow) -> dict[str, Any]:
    return {
        "row_id": row.row_id,
        "timestamp": row.timestamp,
        "features": [str(value) for value in row.features],
        "label": row.label,
    }


def _count_payload(item: ClassCount) -> dict[str, int]:
    return {
        "label": item.label,
        "train_count": item.train_count,
        "validation_count": item.validation_count,
    }


def _result_payload(result: SplitResult, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "mode": result.mode,
        "train_ids": list(result.train_ids),
        "validation_ids": list(result.validation_ids),
        "purged_ids": list(result.purged_ids),
        "class_counts": [_count_payload(item) for item in result.class_counts],
        "train_ratio": str(result.train_ratio),
        "validation_ratio": str(result.validation_ratio),
        "input_hash": result.input_hash,
    }
    if include_hash:
        payload["split_hash"] = result.split_hash
    return payload


def _normalize_rows(items: Iterable[DatasetRow]) -> tuple[DatasetRow, ...]:
    rows = []
    for item in items:
        row_id = item.row_id.strip()
        timestamp = item.timestamp.strip()
        if not row_id or not timestamp:
            raise SplitError("row_id and timestamp are required")
        if not item.features:
            raise SplitError("features cannot be empty")
        features = tuple(_q(value) for value in item.features)
        rows.append(DatasetRow(row_id, timestamp, features, int(item.label)))

    if len(rows) < 2:
        raise SplitError("at least two rows are required")
    if len({row.row_id for row in rows}) != len(rows):
        raise SplitError("duplicate row IDs detected")
    if len({row.timestamp for row in rows}) != len(rows):
        raise SplitError("duplicate timestamps detected")
    return tuple(rows)


def _random_split(
    rows: tuple[DatasetRow, ...],
    validation_count: int,
    seed: int,
    shuffle: bool,
) -> tuple[list[DatasetRow], list[DatasetRow]]:
    ordered = list(rows)
    if shuffle:
        random.Random(seed).shuffle(ordered)
    validation = ordered[:validation_count]
    train = ordered[validation_count:]
    return train, validation


def _stratified_split(
    rows: tuple[DatasetRow, ...],
    validation_ratio: Decimal,
    seed: int,
    shuffle: bool,
) -> tuple[list[DatasetRow], list[DatasetRow]]:
    grouped: dict[int, list[DatasetRow]] = {}
    for row in rows:
        grouped.setdefault(row.label, []).append(row)

    train: list[DatasetRow] = []
    validation: list[DatasetRow] = []
    rng = random.Random(seed)

    for label in sorted(grouped):
        group = list(grouped[label])
        if shuffle:
            rng.shuffle(group)
        val_count = int((Decimal(len(group)) * validation_ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if len(group) > 1:
            val_count = max(1, min(len(group) - 1, val_count))
        else:
            val_count = 0
        validation.extend(group[:val_count])
        train.extend(group[val_count:])

    if shuffle:
        rng.shuffle(train)
        rng.shuffle(validation)
    return train, validation


def _time_series_split(
    rows: tuple[DatasetRow, ...],
    validation_count: int,
    purge_size: int,
) -> tuple[list[DatasetRow], list[DatasetRow], list[DatasetRow]]:
    ordered = sorted(rows, key=lambda row: row.timestamp)
    validation_start = len(ordered) - validation_count
    purge_start = max(0, validation_start - purge_size)
    train = ordered[:purge_start]
    purged = ordered[purge_start:validation_start]
    validation = ordered[validation_start:]
    if not train or not validation:
        raise SplitError("time-series split produced an empty partition")
    return train, validation, purged


def split_dataset(
    rows: Iterable[DatasetRow],
    policy: SplitPolicy | None = None,
) -> SplitResult:
    selected = policy or SplitPolicy()
    data = _normalize_rows(rows)
    validation_count = int(
        (Decimal(len(data)) * _d(selected.validation_ratio)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )
    validation_count = max(1, min(len(data) - 1, validation_count))

    purged: list[DatasetRow] = []
    mode = selected.mode.upper()

    if mode == "RANDOM":
        train, validation = _random_split(
            data,
            validation_count,
            selected.random_seed,
            selected.shuffle,
        )
    elif mode == "STRATIFIED":
        train, validation = _stratified_split(
            data,
            _d(selected.validation_ratio),
            selected.random_seed,
            selected.shuffle,
        )
    else:
        train, validation, purged = _time_series_split(
            data,
            validation_count,
            selected.purge_size,
        )

    if not train or not validation:
        raise SplitError("split produced an empty partition")

    train_ids = tuple(row.row_id for row in train)
    validation_ids = tuple(row.row_id for row in validation)
    purged_ids = tuple(row.row_id for row in purged)

    if set(train_ids) & set(validation_ids):
        raise SplitError("train/validation leakage detected")
    if set(train_ids) & set(purged_ids):
        raise SplitError("train/purge leakage detected")
    if set(validation_ids) & set(purged_ids):
        raise SplitError("validation/purge leakage detected")

    labels = sorted({row.label for row in data})
    train_label_map = {row.row_id: row.label for row in train}
    validation_label_map = {row.row_id: row.label for row in validation}
    class_counts = tuple(
        ClassCount(
            label=label,
            train_count=sum(1 for item in train_label_map.values() if item == label),
            validation_count=sum(1 for item in validation_label_map.values() if item == label),
        )
        for label in labels
    )

    usable_count = len(train) + len(validation)
    result = SplitResult(
        version=VERSION,
        mode=mode,
        train_ids=train_ids,
        validation_ids=validation_ids,
        purged_ids=purged_ids,
        class_counts=class_counts,
        train_ratio=_q(Decimal(len(train)) / Decimal(usable_count)),
        validation_ratio=_q(Decimal(len(validation)) / Decimal(usable_count)),
        input_hash=_hash({
            "rows": [_row_payload(row) for row in data],
            "policy": {
                "validation_ratio": str(selected.validation_ratio),
                "mode": selected.mode.upper(),
                "shuffle": selected.shuffle,
                "random_seed": selected.random_seed,
                "purge_size": selected.purge_size,
            },
        }),
        split_hash="",
    )
    return replace(result, split_hash=_hash(_result_payload(result)))


def verify_result(result: SplitResult) -> bool:
    if result.version != VERSION:
        raise SplitError("unsupported split version")
    if result.mode not in {"RANDOM", "STRATIFIED", "TIME_SERIES"}:
        raise SplitError("invalid split mode")
    if not result.train_ids or not result.validation_ids:
        raise SplitError("train and validation sets must be non-empty")

    train = set(result.train_ids)
    validation = set(result.validation_ids)
    purged = set(result.purged_ids)

    if train & validation or train & purged or validation & purged:
        raise SplitError("partition leakage detected")
    if len(train) != len(result.train_ids):
        raise SplitError("duplicate train IDs detected")
    if len(validation) != len(result.validation_ids):
        raise SplitError("duplicate validation IDs detected")
    if _q(result.train_ratio + result.validation_ratio) != Decimal("1.0000"):
        raise SplitError("train and validation ratios must sum to one")

    clean = replace(result, split_hash="")
    if result.split_hash != _hash(_result_payload(clean)):
        raise SplitError("split hash mismatch")
    return True


def save_result(result: SplitResult, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_result_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> SplitResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = SplitResult(
        version=payload["version"],
        mode=payload["mode"],
        train_ids=tuple(payload["train_ids"]),
        validation_ids=tuple(payload["validation_ids"]),
        purged_ids=tuple(payload["purged_ids"]),
        class_counts=tuple(
            ClassCount(
                label=int(item["label"]),
                train_count=int(item["train_count"]),
                validation_count=int(item["validation_count"]),
            )
            for item in payload["class_counts"]
        ),
        train_ratio=_d(payload["train_ratio"]),
        validation_ratio=_d(payload["validation_ratio"]),
        input_hash=payload["input_hash"],
        split_hash=payload["split_hash"],
    )
    verify_result(result)
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
