from __future__ import annotations
import time
from pathlib import Path

def cleanup(directory: Path, retention_days: int) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    threshold = time.time() - retention_days * 86400
    removed = []
    for path in directory.glob("*.log"):
        if path.stat().st_mtime < threshold:
            path.unlink()
            removed.append(path.name)
    return {"removed": removed, "remaining": len(list(directory.glob("*.log")))}
