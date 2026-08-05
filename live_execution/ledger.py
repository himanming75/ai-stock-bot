from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def append_ledger(path: Path, event: dict[str, Any]) -> dict[str, Any]:
    record = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record
