from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rotate_session(
    root: Path,
    *,
    trading_day: str,
    reason: str,
) -> dict[str, Any]:
    actual = root / "release/o4_runtime_resume_session_reporting/actual"
    registry_path = actual / "session_registry.json"
    registry = _read_json(registry_path, {"sessions": []})

    prior = registry["sessions"][-1] if registry["sessions"] else None
    session_number = len(registry["sessions"]) + 1
    session_id = f"session-{trading_day}-{session_number:04d}"

    entry = {
        "session_id": session_id,
        "session_number": session_number,
        "trading_day": trading_day,
        "reason": reason,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": "PREPARED",
        "prior_session_id": prior.get("session_id") if prior else None,
        "automatic_order_replay_enabled": False,
        "automatic_broker_restart_enabled": False,
    }
    registry["sessions"].append(entry)

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(registry, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return entry
