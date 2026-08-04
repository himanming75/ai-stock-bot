from __future__ import annotations
from typing import Any

REQUIRED = {"new", "accepted", "partially_filled", "filled", "canceled"}

def coverage(events: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(row.get("status", "")).lower() for row in events}
    covered = REQUIRED & observed
    pct = len(covered) / len(REQUIRED) * 100
    return {
        "required": sorted(REQUIRED),
        "observed": sorted(observed),
        "covered": sorted(covered),
        "coverage_pct": round(pct, 4),
    }
