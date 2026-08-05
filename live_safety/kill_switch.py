from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def default_state() -> dict[str, Any]:
    return {
        "live_kill_switch_active": True,
        "reason": "L1_DEFAULT_ACTIVE",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def ensure_live_kill_switch(path: Path) -> dict[str, Any]:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(default_state(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return json.loads(path.read_text(encoding="utf-8-sig"))


def activate_live_kill_switch(path: Path, reason: str) -> dict[str, Any]:
    value = {
        "live_kill_switch_active": True,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
