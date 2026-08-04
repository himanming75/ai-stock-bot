from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from autonomous_paper_session.io import load_json, write_json

def path(root: Path) -> Path:
    return root / "release/v261_01_to_v265_64/control/session_stop.json"

def requested(root: Path) -> bool:
    return load_json(path(root)).get("stop_requested") is True

def request(root: Path, reason: str = "USER_REQUEST") -> dict:
    value = {
        "stop_requested": True,
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(path(root), value)
    return value

def clear(root: Path) -> dict:
    value = {
        "stop_requested": False,
        "reason": "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(path(root), value)
    return value
