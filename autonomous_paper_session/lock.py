from __future__ import annotations
import os
from pathlib import Path

class SessionLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        self.acquired = True
        return True

    def release(self) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
        self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError("Another Autonomous Paper Session Runner is already active.")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
