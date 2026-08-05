from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


class RuntimeLockError(RuntimeError):
    pass


def acquire_lock(path: Path, runtime_id: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8-sig"))
        raise RuntimeLockError(
            f"RUNTIME_LOCK_ACTIVE:{existing.get('runtime_id','')}"
        )

    value = {
        "runtime_id": runtime_id,
        "process_id": os.getpid(),
        "acquired_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value


def release_lock(path: Path, runtime_id: str) -> None:
    if not path.exists():
        return
    existing = json.loads(path.read_text(encoding="utf-8-sig"))
    if existing.get("runtime_id") != runtime_id:
        raise RuntimeLockError("RUNTIME_LOCK_OWNER_MISMATCH")
    path.unlink()
