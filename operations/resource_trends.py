from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any


def sample_resources() -> dict[str, Any]:
    sample = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "process_id": os.getpid(),
        "process_time_seconds": time.process_time(),
        "memory_bytes": None,
    }
    try:
        import psutil
        process = psutil.Process(os.getpid())
        sample["memory_bytes"] = process.memory_info().rss
        sample["cpu_percent"] = process.cpu_percent(interval=0.0)
    except Exception:
        sample["cpu_percent"] = None
    return sample


def append_resource_sample(path: Path) -> dict[str, Any]:
    value = sample_resources()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
    return value
