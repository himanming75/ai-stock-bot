from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .models import SchedulerState


class AtomicSchedulerStateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def save(self, state: SchedulerState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            state.to_json_dict(),
            indent=2,
            sort_keys=True,
        ) + "\n"
        fd, temp_name = tempfile.mkstemp(
            prefix=self.path.name + ".",
            suffix=".tmp",
            dir=str(self.path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def load(self) -> SchedulerState | None:
        if not self.path.exists():
            return None
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("scheduler state must be a JSON object")
        state = SchedulerState.from_json_dict(raw)
        if state.schema_version != 1:
            raise ValueError("unsupported scheduler state schema")
        return state
