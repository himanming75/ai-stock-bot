from __future__ import annotations

"""
V27.4 Offline Data Normalization Engine

Features:
- Z-score scaling
- Min-max scaling
- Robust scaling using median and IQR
- Optional log transform
- Winsorization
- Missing-value handling
- Fit/transform separation to prevent leakage
- Per-feature statistics
- Deterministic output
- SHA-256 integrity verification
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
from statistics import median
from typing import Any, Iterable
import json
import math

VERSION = "27.4"
ZERO = Decimal("0")
FOUR = Decimal("0.0001")


class NormalizationError(ValueError):
    pass


def _d(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise NormalizationError(f"invalid decimal value: {value!r}") from exc
    if not result.is_finite():
        raise NormalizationError("decimal value must be finite")
    return result


def _q(value: Any) -> Decimal:
    return _d(value).quantize(FOUR, rounding=ROUND_HALF_UP)


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_canonical(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DataRow:
    row_id: str
    values: tuple[Decimal | None, ...]


@dataclass(frozen=True)
class NormalizationPolicy:
    method: str = "ZSCORE"
    missing_strategy: str = "MEDIAN"
    winsor_lower_pct: Decimal = Decimal("0")
    winsor_upper_pct: Decimal = Decimal("100")
    log_transform: bool = False
    log_offset: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if self.method.upper() not in {"ZSCORE", "MINMAX", "ROBUST"}:
            raise NormalizationError("unsupported normalization method")
        if self.missing_strategy.upper() not in {"MEDIAN", "MEAN", "ZERO", "ERROR"}:
            raise NormalizationError("unsupported missing strategy")
        lower = _d(self.winsor_lower_pct)
        upper = _d(self.winsor_upper_pct)
        if lower < ZERO or upper > Decimal("100") or lower >= upper:
            raise NormalizationError("invalid winsorization percentiles")
        if _d(self.log_offset) <= ZERO:
            raise NormalizationError("log_offset must be positive")


@dataclass(frozen=True)
class FeatureStats:
    index: int
    fill_value: Decimal
    minimum: Decimal
    maximum: Decimal
    mean: Decimal
    stddev: Decimal
    median: Decimal
    q1: Decimal
    q3: Decimal
    lower_clip: Decimal
    upper_clip: Decimal


@dataclass(frozen=True)
class FittedNormalizer:
    version: str
    method: str
    feature_count: int
    policy: NormalizationPolicy
    stats: tuple[FeatureStats, ...]
    fit_hash: str


@dataclass(frozen=True)
class NormalizedRow:
    row_id: str
    values: tuple[Decimal, ...]
    row_hash: str


@dataclass(frozen=True)
class NormalizedSet:
    version: str
    method: str
    rows: tuple[NormalizedRow, ...]
    fit_hash: str
    output_hash: str


def _policy_payload(policy: NormalizationPolicy) -> dict[str, Any]:
    return {
        "method": policy.method.upper(),
        "missing_strategy": policy.missing_strategy.upper(),
        "winsor_lower_pct": str(policy.winsor_lower_pct),
        "winsor_upper_pct": str(policy.winsor_upper_pct),
        "log_transform": policy.log_transform,
        "log_offset": str(policy.log_offset),
    }


def _stats_payload(stat: FeatureStats) -> dict[str, Any]:
    return {
        "index": stat.index,
        "fill_value": str(stat.fill_value),
        "minimum": str(stat.minimum),
        "maximum": str(stat.maximum),
        "mean": str(stat.mean),
        "stddev": str(stat.stddev),
        "median": str(stat.median),
        "q1": str(stat.q1),
        "q3": str(stat.q3),
        "lower_clip": str(stat.lower_clip),
        "upper_clip": str(stat.upper_clip),
    }


def _fit_payload(fitted: FittedNormalizer, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": fitted.version,
        "method": fitted.method,
        "feature_count": fitted.feature_count,
        "policy": _policy_payload(fitted.policy),
        "stats": [_stats_payload(stat) for stat in fitted.stats],
    }
    if include_hash:
        payload["fit_hash"] = fitted.fit_hash
    return payload


def _row_payload(row: NormalizedRow, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "row_id": row.row_id,
        "values": [str(value) for value in row.values],
    }
    if include_hash:
        payload["row_hash"] = row.row_hash
    return payload


def _set_payload(result: NormalizedSet, include_hash: bool = False) -> dict[str, Any]:
    payload = {
        "version": result.version,
        "method": result.method,
        "rows": [_row_payload(row, include_hash=True) for row in result.rows],
        "fit_hash": result.fit_hash,
    }
    if include_hash:
        payload["output_hash"] = result.output_hash
    return payload


def _normalize_rows(items: Iterable[DataRow]) -> tuple[DataRow, ...]:
    rows = []
    feature_count = None
    for item in items:
        row_id = item.row_id.strip()
        if not row_id:
            raise NormalizationError("row_id is required")
        if feature_count is None:
            feature_count = len(item.values)
            if feature_count == 0:
                raise NormalizationError("feature vector cannot be empty")
        if len(item.values) != feature_count:
            raise NormalizationError("inconsistent feature count")
        values = tuple(None if value is None else _d(value) for value in item.values)
        rows.append(DataRow(row_id, values))

    if not rows:
        raise NormalizationError("rows cannot be empty")
    if len({row.row_id for row in rows}) != len(rows):
        raise NormalizationError("duplicate row IDs detected")
    return tuple(rows)


def _percentile(values: list[Decimal], pct: Decimal) -> Decimal:
    if not values:
        raise NormalizationError("percentile requires data")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = float(pct / Decimal("100")) * (len(ordered) - 1)
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    weight = Decimal(str(rank - lower))
    return ordered[lower] * (Decimal("1") - weight) + ordered[upper] * weight


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _stddev(values: list[Decimal], avg: Decimal) -> Decimal:
    if len(values) <= 1:
        return ZERO
    variance = sum((value - avg) ** 2 for value in values) / Decimal(len(values))
    return _d(math.sqrt(float(variance)))


def _quartiles(values: list[Decimal]) -> tuple[Decimal, Decimal]:
    return _percentile(values, Decimal("25")), _percentile(values, Decimal("75"))


def fit_normalizer(
    rows: Iterable[DataRow],
    policy: NormalizationPolicy | None = None,
) -> FittedNormalizer:
    selected = policy or NormalizationPolicy()
    data = _normalize_rows(rows)
    feature_count = len(data[0].values)
    stats = []

    for index in range(feature_count):
        observed = [row.values[index] for row in data if row.values[index] is not None]
        observed = [_d(value) for value in observed]
        if not observed:
            raise NormalizationError(f"feature {index} contains only missing values")

        mean_value = _mean(observed)
        median_value = _d(median([float(value) for value in observed]))
        q1, q3 = _quartiles(observed)
        stddev_value = _stddev(observed, mean_value)

        strategy = selected.missing_strategy.upper()
        if strategy == "MEDIAN":
            fill_value = median_value
        elif strategy == "MEAN":
            fill_value = mean_value
        elif strategy == "ZERO":
            fill_value = ZERO
        else:
            if any(row.values[index] is None for row in data):
                raise NormalizationError("missing value encountered with ERROR strategy")
            fill_value = median_value

        lower_clip = _percentile(observed, _d(selected.winsor_lower_pct))
        upper_clip = _percentile(observed, _d(selected.winsor_upper_pct))

        transformed = []
        for value in observed:
            clipped = max(lower_clip, min(upper_clip, value))
            if selected.log_transform:
                shifted = clipped + _d(selected.log_offset)
                if shifted <= ZERO:
                    raise NormalizationError("log transform received non-positive shifted value")
                clipped = _d(math.log(float(shifted)))
            transformed.append(clipped)

        transformed_mean = _mean(transformed)
        transformed_median = _d(median([float(value) for value in transformed]))
        transformed_q1, transformed_q3 = _quartiles(transformed)
        transformed_stddev = _stddev(transformed, transformed_mean)

        stats.append(FeatureStats(
            index=index,
            fill_value=_q(fill_value),
            minimum=_q(min(transformed)),
            maximum=_q(max(transformed)),
            mean=_q(transformed_mean),
            stddev=_q(transformed_stddev),
            median=_q(transformed_median),
            q1=_q(transformed_q1),
            q3=_q(transformed_q3),
            lower_clip=_q(lower_clip),
            upper_clip=_q(upper_clip),
        ))

    fitted = FittedNormalizer(
        version=VERSION,
        method=selected.method.upper(),
        feature_count=feature_count,
        policy=selected,
        stats=tuple(stats),
        fit_hash="",
    )
    return replace(fitted, fit_hash=_hash(_fit_payload(fitted)))


def _transform_value(value: Decimal | None, stat: FeatureStats, policy: NormalizationPolicy) -> Decimal:
    raw = stat.fill_value if value is None else _d(value)
    clipped = max(stat.lower_clip, min(stat.upper_clip, raw))
    if policy.log_transform:
        shifted = clipped + _d(policy.log_offset)
        if shifted <= ZERO:
            raise NormalizationError("log transform received non-positive shifted value")
        clipped = _d(math.log(float(shifted)))

    method = policy.method.upper()
    if method == "ZSCORE":
        if stat.stddev == ZERO:
            return ZERO
        return _q((clipped - stat.mean) / stat.stddev)
    if method == "MINMAX":
        span = stat.maximum - stat.minimum
        if span == ZERO:
            return ZERO
        return _q((clipped - stat.minimum) / span)

    iqr = stat.q3 - stat.q1
    if iqr == ZERO:
        return ZERO
    return _q((clipped - stat.median) / iqr)


def transform_rows(
    rows: Iterable[DataRow],
    fitted: FittedNormalizer,
) -> NormalizedSet:
    verify_fitted(fitted)
    data = _normalize_rows(rows)
    if len(data[0].values) != fitted.feature_count:
        raise NormalizationError("feature count does not match fitted normalizer")

    output = []
    for row in data:
        values = tuple(
            _transform_value(row.values[index], fitted.stats[index], fitted.policy)
            for index in range(fitted.feature_count)
        )
        item = NormalizedRow(row.row_id, values, "")
        output.append(replace(item, row_hash=_hash(_row_payload(item))))

    result = NormalizedSet(
        version=VERSION,
        method=fitted.method,
        rows=tuple(output),
        fit_hash=fitted.fit_hash,
        output_hash="",
    )
    return replace(result, output_hash=_hash(_set_payload(result)))


def verify_fitted(fitted: FittedNormalizer) -> bool:
    if fitted.version != VERSION:
        raise NormalizationError("unsupported fitted normalizer version")
    if fitted.method not in {"ZSCORE", "MINMAX", "ROBUST"}:
        raise NormalizationError("invalid method")
    if fitted.feature_count <= 0 or len(fitted.stats) != fitted.feature_count:
        raise NormalizationError("feature statistics mismatch")
    clean = replace(fitted, fit_hash="")
    if fitted.fit_hash != _hash(_fit_payload(clean)):
        raise NormalizationError("fit hash mismatch")
    return True


def verify_result(result: NormalizedSet) -> bool:
    if result.version != VERSION:
        raise NormalizationError("unsupported normalized-set version")
    if result.method not in {"ZSCORE", "MINMAX", "ROBUST"}:
        raise NormalizationError("invalid normalization method")
    if not result.rows:
        raise NormalizationError("normalized set cannot be empty")
    if len({row.row_id for row in result.rows}) != len(result.rows):
        raise NormalizationError("duplicate normalized row IDs detected")
    for row in result.rows:
        clean_row = replace(row, row_hash="")
        if row.row_hash != _hash(_row_payload(clean_row)):
            raise NormalizationError("normalized row hash mismatch")
    clean = replace(result, output_hash="")
    if result.output_hash != _hash(_set_payload(clean)):
        raise NormalizationError("normalized-set hash mismatch")
    return True


def save_fitted(fitted: FittedNormalizer, path: str | Path) -> Path:
    verify_fitted(fitted)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_fit_payload(fitted, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_fitted(path: str | Path) -> FittedNormalizer:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    policy_data = payload["policy"]
    policy = NormalizationPolicy(
        method=policy_data["method"],
        missing_strategy=policy_data["missing_strategy"],
        winsor_lower_pct=_d(policy_data["winsor_lower_pct"]),
        winsor_upper_pct=_d(policy_data["winsor_upper_pct"]),
        log_transform=bool(policy_data["log_transform"]),
        log_offset=_d(policy_data["log_offset"]),
    )
    fitted = FittedNormalizer(
        version=payload["version"],
        method=payload["method"],
        feature_count=int(payload["feature_count"]),
        policy=policy,
        stats=tuple(
            FeatureStats(
                index=int(item["index"]),
                fill_value=_d(item["fill_value"]),
                minimum=_d(item["minimum"]),
                maximum=_d(item["maximum"]),
                mean=_d(item["mean"]),
                stddev=_d(item["stddev"]),
                median=_d(item["median"]),
                q1=_d(item["q1"]),
                q3=_d(item["q3"]),
                lower_clip=_d(item["lower_clip"]),
                upper_clip=_d(item["upper_clip"]),
            )
            for item in payload["stats"]
        ),
        fit_hash=payload["fit_hash"],
    )
    verify_fitted(fitted)
    return fitted


def save_result(result: NormalizedSet, path: str | Path) -> Path:
    verify_result(result)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_set_payload(result, include_hash=True), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


def load_result(path: str | Path) -> NormalizedSet:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    result = NormalizedSet(
        version=payload["version"],
        method=payload["method"],
        rows=tuple(
            NormalizedRow(
                row_id=item["row_id"],
                values=tuple(_d(value) for value in item["values"]),
                row_hash=item["row_hash"],
            )
            for item in payload["rows"]
        ),
        fit_hash=payload["fit_hash"],
        output_hash=payload["output_hash"],
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
