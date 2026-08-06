from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import SourceHealth


def _parse_time(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


def load_json_snapshot(
    path: Path,
    *,
    broker: str,
    stale_after_seconds: float = 900,
) -> tuple[dict, SourceHealth]:
    if not path.exists():
        return {}, SourceHealth(
            broker=broker,
            source_path=str(path),
            available=False,
            generated_at=None,
            age_seconds=None,
            freshness="MISSING",
            error="FILE_NOT_FOUND",
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        return {}, SourceHealth(
            broker=broker,
            source_path=str(path),
            available=False,
            generated_at=None,
            age_seconds=None,
            freshness="INVALID",
            error=str(exc),
        )

    generated_at = (
        payload.get("generated_at")
        or payload.get("timestamp")
        or payload.get("created_at")
    )
    parsed = _parse_time(generated_at)
    age_seconds = None
    freshness = "UNKNOWN"
    if parsed is not None:
        now = datetime.now(timezone.utc)
        age_seconds = max(
            (now - parsed.astimezone(timezone.utc)).total_seconds(),
            0,
        )
        freshness = (
            "FRESH"
            if age_seconds <= stale_after_seconds
            else "STALE"
        )

    return payload, SourceHealth(
        broker=broker,
        source_path=str(path),
        available=True,
        generated_at=generated_at,
        age_seconds=age_seconds,
        freshness=freshness,
        error=None,
    )
