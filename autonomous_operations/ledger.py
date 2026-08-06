from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path


class GlobalLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: dict) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        payload = dict(event)
        payload["recorded_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    payload,
                    sort_keys=True,
                ) + "\n"
            )
