from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


class RunLock:
    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "pid": os.getpid(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            descriptor = os.open(
                self.path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise RuntimeError(
                f"orchestrator lock already exists: {self.path}"
            ) from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        self.acquired = True

    def release(self) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
        self.acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
