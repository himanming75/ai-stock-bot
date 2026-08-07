from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {
                "last_completed_cycle": 0,
                "last_cycle_id": None,
                "state": "NEW",
            }
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, *, cycle_number: int, cycle_id: str, state: str, summary: dict) -> None:
        payload = {
            "last_completed_cycle": cycle_number,
            "last_cycle_id": cycle_id,
            "state": state,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.path)
