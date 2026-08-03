from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

def evaluate_snapshot_freshness(
    observed_at: str,
    maximum_age_seconds: int,
) -> dict[str, Any]:
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_seconds = max(0.0, (now - observed).total_seconds())
    except Exception:
        return {
            "passed": False,
            "age_seconds": None,
            "maximum_age_seconds": maximum_age_seconds,
            "reason": "INVALID_OBSERVED_AT",
        }

    return {
        "passed": age_seconds <= maximum_age_seconds,
        "age_seconds": round(age_seconds, 3),
        "maximum_age_seconds": maximum_age_seconds,
        "reason": "",
    }
