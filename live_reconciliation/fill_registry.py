from __future__ import annotations
import json
from pathlib import Path


class DuplicateLiveFillError(RuntimeError):
    pass


class LiveFillRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {"fill_keys": []}
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def reserve(self, fill_key: str) -> None:
        value = self._read()
        if fill_key in value["fill_keys"]:
            raise DuplicateLiveFillError("DUPLICATE_LIVE_FILL")
        value["fill_keys"].append(fill_key)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
