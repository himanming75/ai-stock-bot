from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import os
import tempfile


@dataclass(frozen=True)
class RecoverySnapshot:
    state: str
    captured_at: datetime
    heartbeat_count: int
    scheduler: list[dict[str, Any]]
    metadata: dict[str, Any]


class JsonRecoveryStore:
    """Atomic JSON snapshot store suitable for local paper-runtime recovery."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def save(self, snapshot: RecoverySnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(snapshot)
        data["captured_at"] = snapshot.captured_at.isoformat()
        payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=self.path.parent,
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def load(self) -> RecoverySnapshot | None:
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return RecoverySnapshot(
            state=data["state"],
            captured_at=datetime.fromisoformat(data["captured_at"]),
            heartbeat_count=int(data["heartbeat_count"]),
            scheduler=list(data["scheduler"]),
            metadata=dict(data["metadata"]),
        )
