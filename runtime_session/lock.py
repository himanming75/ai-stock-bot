from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path

from .io import read_json, write_json


class SessionAlreadyActive(RuntimeError):
    pass


class SessionLock:
    def __init__(self, path: Path) -> None:
        self.path = path

    def acquire(self, session_id: str) -> None:
        if self.path.exists():
            current = read_json(self.path)
            raise SessionAlreadyActive(
                f"SESSION_LOCK_EXISTS:{current.get('session_id', 'UNKNOWN')}"
            )
        write_json(self.path, {
            "session_id": session_id,
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        })

    def release(self, session_id: str) -> None:
        if not self.path.exists():
            return
        current = read_json(self.path)
        if current.get("session_id") != session_id:
            raise RuntimeError("SESSION_LOCK_OWNER_MISMATCH")
        self.path.unlink()
