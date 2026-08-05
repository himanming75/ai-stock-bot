from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

class WatchdogStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "restart_attempts": [],
                "last_controller_exit_code": None,
                "state": "NEW",
            }
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def save(self, payload: dict) -> None:
        payload = dict(payload)
        payload["saved_at"] = datetime.now(timezone.utc).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp.replace(self.path)
