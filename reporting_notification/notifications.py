from __future__ import annotations
from datetime import datetime, time, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class QuietHoursPolicy:
    def evaluate(
        self,
        *,
        observed_at: datetime,
        start_hour: int = 22,
        end_hour: int = 7,
    ) -> dict[str, Any]:
        hour = observed_at.hour
        quiet = hour >= start_hour or hour < end_hour
        return {
            "quiet_hours_active": quiet,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "observed_hour": hour,
        }


class AlertDeduplicator:
    def fingerprint(self, alert: dict[str, Any]) -> str:
        raw = json.dumps(
            {
                "category": alert.get("category"),
                "severity": alert.get("severity"),
                "subject": alert.get("subject"),
                "message": alert.get("message"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class NotificationPreviewQueue:
    SUPPORTED_CHANNELS = {"EMAIL", "SLACK", "DISCORD", "TELEGRAM"}

    def __init__(self, path: Path) -> None:
        self.path = path

    def enqueue(
        self,
        *,
        channel: str,
        alert: dict[str, Any],
        quiet_hours: dict[str, Any],
    ) -> dict[str, Any]:
        channel = channel.upper()
        if channel not in self.SUPPORTED_CHANNELS:
            raise ValueError("UNSUPPORTED_CHANNEL")

        fingerprint = AlertDeduplicator().fingerprint(alert)
        state = (
            "HELD_QUIET_HOURS"
            if quiet_hours["quiet_hours_active"]
            else "READY_PREVIEW"
        )
        record = {
            "notification_id": "notify-" + fingerprint,
            "channel": channel,
            "fingerprint": fingerprint,
            "state": state,
            "alert": alert,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "external_send_allowed": False,
            "external_send_performed": False,
            "network_used": False,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    existing.add(json.loads(line)["fingerprint"])
        if fingerprint not in existing:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            record["duplicate_suppressed"] = False
        else:
            record["duplicate_suppressed"] = True
            record["state"] = "DUPLICATE_SUPPRESSED"
        return record

    def send(self, notification_id: str) -> None:
        raise RuntimeError(f"EXTERNAL_NOTIFICATION_SEND_DISABLED:{notification_id}")
