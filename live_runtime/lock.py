from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path


class LiveRuntimeAlreadyRunning(RuntimeError):
    pass


class LiveRuntimeLock:
    def __init__(self, path: Path) -> None:
        self.path = path

    def acquire(self, runtime_id: str) -> None:
        if self.path.exists():
            raise LiveRuntimeAlreadyRunning("LIVE_RUNTIME_LOCK_EXISTS")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({
                "runtime_id": runtime_id,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def release(self) -> None:
        if self.path.exists():
            self.path.unlink()
