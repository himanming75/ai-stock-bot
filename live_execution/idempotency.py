from __future__ import annotations
import json
from pathlib import Path


class DuplicateLiveOrderError(RuntimeError):
    pass


class LiveIdempotencyRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {"request_hashes": []}
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def reserve(self, request_hash: str) -> None:
        value = self._read()
        if request_hash in value["request_hashes"]:
            raise DuplicateLiveOrderError("DUPLICATE_LIVE_REQUEST")
        value["request_hashes"].append(request_hash)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
