from __future__ import annotations
import json
from pathlib import Path


class DuplicateLiveCycleError(RuntimeError):
    pass


class LiveCycleRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {"cycle_ids": []}
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def reserve(self, cycle_id: str) -> None:
        value = self._read()
        if cycle_id in value["cycle_ids"]:
            raise DuplicateLiveCycleError("DUPLICATE_LIVE_CYCLE")
        value["cycle_ids"].append(cycle_id)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
