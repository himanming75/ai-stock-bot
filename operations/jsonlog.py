from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {
    "api_key", "secret_key", "token", "password",
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("***REDACTED***" if key in SENSITIVE_KEYS else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class JsonEventLogger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def write(
        self,
        event: str,
        *,
        level: str = "INFO",
        component: str = "operations",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "component": component,
            "event": event,
            "payload": redact(payload or {}),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record
