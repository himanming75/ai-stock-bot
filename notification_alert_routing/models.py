from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


SEVERITY_RANK = {
    "INFO": 10,
    "WARNING": 20,
    "CRITICAL": 30,
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def event_key(source: str, code: str, context: dict) -> str:
    stable = json.dumps(
        {
            "source": source,
            "code": code,
            "context": context,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def message_id(key: str, generated_at: str) -> str:
    raw = f"{key}:{generated_at}"
    return "alert_" + hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:24]
