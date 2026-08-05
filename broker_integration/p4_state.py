from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def write_heartbeat(
    path: Path,
    *,
    runtime_id: str,
    cycle_number: int,
    state: str,
) -> dict[str, Any]:
    value = {
        "runtime_id": runtime_id,
        "cycle_number": cycle_number,
        "state": state,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(path, value)
    return value


def write_checkpoint(
    path: Path,
    *,
    runtime_id: str,
    cycle_number: int,
    cycle_id: str,
    state: str,
    blockers: list[str],
) -> dict[str, Any]:
    value = {
        "stage": "P4",
        "runtime_id": runtime_id,
        "cycle_number": cycle_number,
        "cycle_id": cycle_id,
        "state": state,
        "blockers": blockers,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(path, value)
    return value
