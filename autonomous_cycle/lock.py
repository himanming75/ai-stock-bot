from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from autonomous_cycle.io import load_json, write_json

def acquire_lock(
    path: Path,
    cycle_id: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    current = load_json(path)
    if current:
        expires_at_text = current.get("expires_at")
        try:
            expires_at = datetime.fromisoformat(expires_at_text)
        except Exception:
            expires_at = now - timedelta(seconds=1)
        if expires_at > now and current.get("cycle_id") != cycle_id:
            return {
                "acquired": False,
                "reason": "ACTIVE_CYCLE_LOCK",
                "blocking_cycle_id": current.get("cycle_id"),
                "expires_at": current.get("expires_at"),
            }

    expires_at = now + timedelta(seconds=max(1, timeout_seconds))
    body = {
        "cycle_id": cycle_id,
        "acquired_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "state": "LOCKED",
    }
    write_json(path, body)
    return {"acquired": True, **body}

def release_lock(path: Path, cycle_id: str) -> dict[str, Any]:
    current = load_json(path)
    if current.get("cycle_id") != cycle_id:
        return {"released": False, "reason": "LOCK_OWNER_MISMATCH"}
    if path.exists():
        path.unlink()
    return {"released": True, "cycle_id": cycle_id}
