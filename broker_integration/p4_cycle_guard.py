from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def cycle_id(
    runtime_id: str,
    cycle_number: int,
    trading_day: str,
) -> str:
    raw = f"{runtime_id}|{cycle_number}|{trading_day}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"cycles": {}}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def reserve_cycle(
    path: Path,
    *,
    runtime_id: str,
    cycle_number: int,
    trading_day: str,
) -> tuple[bool, str]:
    value = load_registry(path)
    cycles = value.setdefault("cycles", {})
    identifier = cycle_id(runtime_id, cycle_number, trading_day)
    if identifier in cycles:
        return False, identifier

    cycles[identifier] = {
        "runtime_id": runtime_id,
        "cycle_number": cycle_number,
        "trading_day": trading_day,
        "reserved_at": datetime.now(timezone.utc).isoformat(),
        "state": "RESERVED",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return True, identifier


def update_cycle(
    path: Path,
    identifier: str,
    **changes: Any,
) -> None:
    value = load_registry(path)
    cycles = value.setdefault("cycles", {})
    if identifier not in cycles:
        raise KeyError("CYCLE_NOT_RESERVED")
    cycles[identifier].update(changes)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
