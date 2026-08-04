from __future__ import annotations
import hashlib
import json
from datetime import datetime
from typing import Iterable


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def analyze(rows: list[dict], expected_interval_seconds: int) -> dict:
    timestamps: list[datetime] = []
    invalid_timestamps = 0
    fingerprints: set[str] = set()
    duplicates = 0
    for row in rows:
        stamp = _parse(row.get("observed_at"))
        if stamp is None:
            invalid_timestamps += 1
        else:
            timestamps.append(stamp)
        normalized = dict(row)
        normalized.pop("recorded_at", None)
        digest = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode("utf-8")).hexdigest()
        if digest in fingerprints:
            duplicates += 1
        fingerprints.add(digest)

    timestamps.sort()
    gaps = [(b - a).total_seconds() for a, b in zip(timestamps, timestamps[1:])]
    duration = (timestamps[-1] - timestamps[0]).total_seconds() if len(timestamps) >= 2 else 0.0
    max_gap = max(gaps, default=0.0)
    threshold = max(expected_interval_seconds * 3, expected_interval_seconds + 30)
    excessive = sum(1 for gap in gaps if gap > threshold)
    return {
        "timestamp_count": len(timestamps),
        "invalid_timestamp_count": invalid_timestamps,
        "duplicate_record_count": duplicates,
        "observation_duration_seconds": round(duration, 3),
        "maximum_gap_seconds": round(max_gap, 3),
        "excessive_gap_count": excessive,
        "gap_threshold_seconds": threshold,
    }
