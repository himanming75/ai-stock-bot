from __future__ import annotations
import time
from pathlib import Path

def inspect(path: Path, stale_minutes: int) -> dict:
    if not path.exists():
        return {"present": False, "stale": False, "removed": False}
    age_seconds = max(0.0, time.time() - path.stat().st_mtime)
    stale = age_seconds >= stale_minutes * 60
    return {
        "present": True,
        "stale": stale,
        "removed": False,
        "age_seconds": round(age_seconds, 2),
    }

def remove_if_stale(path: Path, stale_minutes: int) -> dict:
    result = inspect(path, stale_minutes)
    if result.get("stale") and path.exists():
        path.unlink()
        result["removed"] = True
    return result
