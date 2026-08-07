from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path

class InstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
            pid = int(payload.get("pid", 0) or 0)
            if pid and self._pid_exists(pid):
                raise RuntimeError(f"CONTROLLER_ALREADY_RUNNING:{pid}")
        payload = {
            "pid": os.getpid(),
            "acquired_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self.acquired = True

    def release(self) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
        self.acquired = False

    @staticmethod
    def _pid_exists(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
